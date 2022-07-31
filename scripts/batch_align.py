#! /usr/bin/env python3

import argparse
import atexit
import collections
import concurrent.futures
import logging
import os
import re
import shutil
import sys
import stat
import subprocess
import tarfile
import tempfile
import threading

from contextlib import contextmanager
from pathlib import Path
from pprint import pprint
from subprocess import check_output
from subprocess import PIPE
from subprocess import Popen
from timeit import default_timer as timer
from xopen import xopen
import time
import shlex
from fcntl import fcntl
try:
    from fcntl import F_SETPIPE_SZ
except ImportError:
    # ref: linux uapi/linux/fcntl.h
    F_SETPIPE_SZ = 1024 + 7
from select import select



# ./scripts/batch_align.py asms/chlamydia_pecorum__01.tar.xz ./intermediate/02_filter/gc01_1kl.fa

logging.basicConfig(stream=sys.stderr,
                    level=logging.INFO,
                    format='[%(asctime)s] (%(levelname)s) %(message)s')


def readfq(fp):  # this is a generator function
    # From https://github.com/lh3/readfq/blob/master/readfq.py
    last = None  # this is a buffer keeping the last unprocessed line
    while True:  # mimic closure; is it a bad idea?
        if not last:  # the first record or a record following a fastq
            for l in fp:  # search for the start of the next record
                if l[0] in '>@':  # fasta/q header line
                    last = l[:-1]  # save this line
                    break
        if not last: break

        ####
        # modified to include comments
        ####
        #name, seqs, last = last[1:].partition(" ")[0], [], None
        name, _, comment = last[1:].partition(" ")
        seqs = []
        last = None
        ####
        # end of the modified part
        ####

        for l in fp:  # read the sequence
            if l[0] in '@+>':
                last = l[:-1]
                break
            seqs.append(l[:-1])
        if not last or last[0] != '+':  # this is a fasta record
            yield name, comment, ''.join(seqs), None  # yield a fasta record
            if not last: break
        else:  # this is a fastq record
            seq, leng, seqs = ''.join(seqs), 0, []
            for l in fp:  # read the quality
                seqs.append(l[:-1])
                leng += len(l) - 1
                if leng >= len(seq):  # have read enough quality
                    last = None
                    yield name, comment, seq, ''.join(seqs)
                    # yield a fastq record
                    break
            if last:  # reach EOF before reading enough quality
                yield name, comment, seq, None  # yield a fasta record instead
                break


def iterate_over_batch(asms_fn, selected_rnames):
    logging.info(f"Opening {asms_fn}")
    skipped = 0
    with tarfile.open(asms_fn, mode="r:xz") as tar:
        for member in tar.getmembers():
            # extract file headers
            name = member.name
            rname = Path(name).stem
            if rname not in selected_rnames:
                logging.debug(f"Skipping {rname} ({name})")
                skipped += 1
                continue
            # extract file content
            if skipped > 0:
                logging.info(f"Skipping {skipped} references in {asms_fn}")
                skipped = 0
            logging.info(f"Extracting {rname} ({name})")
            f = tar.extractfile(member)
            rfa = f.read()
            yield rname, rfa
    if skipped > 0:
        logging.info(f"Skipping {skipped} references in {asms_fn}")


def load_qdicts(query_fn):
    qname_to_qfa = collections.OrderedDict()
    rname_to_qnames = collections.defaultdict(lambda: [])
    with xopen(query_fn) as fo:
        for qname, qcom, qseq, qquals in readfq(fo):
            qname_to_qfa[qname] = f">{qname}\n{qseq}"
            rnames = qcom.split(",")
            for rname in rnames:
                rname_to_qnames[rname].append(qname)
    return qname_to_qfa, rname_to_qnames


@contextmanager
def named_pipe():
    dirname = tempfile.mkdtemp()
    try:
        path = os.path.join(dirname, 'named_pipe')
        os.mkfifo(path)
        yield path
    finally:
        shutil.rmtree(dirname)


def get_pipe_buffer_size():
    # see https://unix.stackexchange.com/a/11954 for the pipe buffer capacities returned here
    if sys.platform == "linux":
        return 2**20  # 1MB is the max on linux
    elif sys.platform == "darwin":
        return 2**14  # 64KB is the max on darwin
    else:
        raise OSError("Unsupported platform")


def _write_to_pipe(pipe_path, data):
    byte_start = 0
    buffer_size = get_pipe_buffer_size()
    with open(pipe_path, 'wb', buffering=0) as outstream:
        try:
            # set pipe buffer size
            fd = outstream.fileno()
            fcntl(fd, F_SETPIPE_SZ, buffer_size)
        except OSError as error:
            logging.error("Failed to set pipe buffer size: " + str(error))
            sys.exit(1)

        while byte_start < len(data):
            try:
                chunk_to_write = data[byte_start:byte_start + buffer_size]

                # wait for the pipe to be ready to be written to
                select([], [outstream], [])

                # Note: this can throw BrokenPipeError if there is no process (i.e. minimap2) reading from the pipe
                bytes_written = outstream.write(chunk_to_write)
                byte_start += bytes_written

                pipe_buffer_shrunk = bytes_written == 0
                if pipe_buffer_shrunk:
                    buffer_size = buffer_size // 2  # let's reduce the amount we write
                    buffer_size = max(buffer_size, 8)  # we should be able to write at least 8 bytes
                    logging.info(f"[PIPE] Reduced pipe buffer size to {buffer_size}")

            except BrokenPipeError:
                time.sleep(0.1)  # waits minimap2 to get the stream


def run_minimap2(command, qfa):
    logging.info(f"Running command: {command}")
    output = subprocess.check_output(command,
                                     input=qfa,
                                     universal_newlines=True,
                                     stderr=subprocess.DEVNULL)
    return output


def minimap2_4(rfa, qfa, minimap_preset, minimap_threads,
               minimap_extra_params):
    logging.debug(f"Going to run minimap with the following sequences:")
    logging.debug(f"   rfa: {rfa}")
    logging.debug(f"   qfa: {qfa}")

    with named_pipe() as rfn:
        command = [
            "minimap2", "-a", "-x", minimap_preset, "-t",
            str(minimap_threads), *(shlex.split(minimap_extra_params)), rfn,
            '-'
        ]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # we first try to run minimap2 to get the read stream ready, and then try to write the stream
            # this should be slightly more efficient at most
            minimap_2_output = executor.submit(run_minimap2, command, qfa)
            _write_to_pipe(rfn, rfa)
            return minimap_2_output.result()


def minimap2_3(rfa, qfa, minimap_preset):
    logging.debug(f"Going to run minimap with the following sequences:")
    logging.debug(f"   rfa: {rfa}")
    logging.debug(f"   qfa: {qfa}")

    tmpdir = tempfile.mkdtemp()
    rfn = os.path.join(tmpdir, 'ref.fa')
    qfn = os.path.join(tmpdir, 'query.fa')

    logging.debug(f"Temporary dir: {tmpdir}")
    logging.debug(f"Creating fifo files {rfn} and {qfn}")
    #os.mkfifo(rfn)
    #os.mkfifo(qfn)

    logging.debug(f"Opening ref fasta {rfn}")
    with open(rfn, "wb") as rfo:
        logging.debug(f"Opening query fasta {qfn}")
        with open(qfn, "w") as qfo:
            logging.debug(f"Writing to ref fasta")
            rfo.write(rfa)
            logging.debug(f"Writing to query fasta")
            qfo.write(qfa)
    command = ["minimap2", "-a", "--eqx", "-x", minimap_preset, rfn, qfn]
    logging.info(f"Running command: {command}")
    output = check_output(command, timeout=2)
    logging.info(f"Cleaning {tmpdir}")
    os.unlink(rfn)  # Remove file
    os.unlink(qfn)  # Remove file
    os.rmdir(tmpdir)  # Remove directory
    return output.decode("utf-8")


@contextmanager
def temp_fifo():
    """Context Manager for creating named pipes with temporary names."""
    tmpdir = tempfile.mkdtemp()
    filename = os.path.join(tmpdir, 'fifo')  # Temporary filename
    os.mkfifo(filename)  # Create FIFO
    try:
        yield filename
    finally:
        os.unlink(filename)  # Remove file
        os.rmdir(tmpdir)  # Remove directory


def minimap2_2(rfa, qfa, minimap_preset):
    # doesn't work, gets stuck at the first open
    logging.debug(f"Running minimap with the following sequences:")
    logging.debug(f"   rfa: {rfa}")
    logging.debug(f"   qfa: {qfa}")
    with temp_fifo() as rfn:
        logging.debug(f"Opening ref fasta")
        with open(rfn, "w") as rfo:
            with temp_fifo() as qfn:
                logging.debug(f"Opening query fasta")
                with open(qfn, "w") as qfo:
                    logging.debug(f"Writing ref fasta")
                    rfo.write(rfa)
                    logging.debug(f"Writing query fasta")
                    qfo.write(qfa)
                    command = [
                        "minimap2", "-a", "--eqx", "-x", minimap_preset,
                        rfn.name, qfn.name
                    ]
                    logging.info(f"Running command: {command}")
                    output = check_output(command)
                    return output.decode("utf-8")


def minimap2(rfa, qfa, minimap_preset):
    # doesn't always work, sometimes queries get lost and it's probably slower
    # due to files being physical
    logging.debug(f"Running minimap with the following sequences:")
    logging.debug(f"   rfa: {rfa}")
    logging.debug(f"   qfa: {qfa}")
    with tempfile.NamedTemporaryFile("wb", delete=False) as rfile:
        with tempfile.NamedTemporaryFile("wt", delete=False) as qfile:
            rfile.write(rfa)
            rfile.delete = False
            qfile.write(qfa)
            qfile.delete = False

            try:
                #p = Popen(["minimap2", rfile.name, qfile.name])
                command = [
                    "minimap2", "-a", "--eqx", "-x", minimap_preset,
                    rfile.name, qfile.name
                ]
                logging.info(f"Running command: {command}")
                output = check_output(command)
                #p = Popen(["minimap2", rfile.name, qfile.name],
                #        stdout=subprocess.STDOUT)
                #p = Popen(["minimap2", rfile.name, qfile.name],
                #        stdout=PIPE)
                #output = p.communicate()[0]
                # or
                # output = check_output(["pram_axdnull", str(kmer), input_filename,
                #print(output)
                #file.name])
            finally:
                pass
                #os.remove(rfile.name)
                #os.remove(qfile.name)
    return output.decode("utf-8")


def count_alignments(sam):
    j = 0
    #for x in sam.encode("utf8"):
    for x in sam.split("\n"):
        if x and x[0] != "@":
            #logging.info(x)
            j += 1
    return j


def map_queries_to_batch(asms_fn, query_fn, minimap_preset, minimap_threads,
                         minimap_extra_params):
    sstart = timer()
    logging.info(
        f"Mapping queries from '{query_fn}' to '{asms_fn}' using Minimap2 with the '{minimap_preset}' preset"
    )
    qname_to_qfa, rname_to_qnames = load_qdicts(query_fn)

    selected_rnames = set([x for x in rname_to_qnames])
    nsr = len(selected_rnames)
    logging.debug(
        f"Identifying rnames in the query file - #{nsr} records: {selected_rnames}"
    )
    naligns_total = 0
    nrefs = 0
    refs = set()
    for rname, rfa in iterate_over_batch(asms_fn, selected_rnames):
        start = timer()
        refs.add(rname)

        qfas = []
        qnames = []
        for qname in rname_to_qnames[rname]:
            qnames.append(qname)
            qfa = qname_to_qfa[qname]
            qfas.append(qfa)
        logging.info(f"Mapping {qnames} to {rname}")

        result = minimap2_4(rfa, "\n".join(qfas), minimap_preset,
                            minimap_threads, minimap_extra_params)

        assert result and result[
            0] == "@", f"Output of Minimap2 is empty ('{result}')"
        logging.debug(f"Minimap result: {result}")
        print(result, end="")
        naligns = count_alignments(result)
        naligns_total += naligns
        end = timer()
        s = round(1000 * (end - start)) / 1000.0
        n_q = len(qnames)
        logging.info(
            f"Computed {naligns} alignments of {n_q} queries to {rname} in {s} seconds"
        )
    eend = timer()
    ss = round(1000 * (eend - sstart)) / 1000.0
    nrefs = len(refs)
    logging.info(
        f"Finished mapping queries from '{query_fn}' to '{asms_fn}': computed {naligns_total} alignments to {nrefs} references in {ss} seconds"
    )


def main():
    logging.info("Starting")

    parser = argparse.ArgumentParser(description="")

    parser.add_argument(
        '--minimap-preset',
        metavar='str',
        default='sr',
        help='minimap preset [sr]',
    )

    parser.add_argument(
        '--threads',
        type=int,
        default=1,
        help='minimap threads',
    )

    parser.add_argument(
        '--extra-params',
        type=str,
        help='minimap extra parameters',
    )

    parser.add_argument(
        'batch_fn',
        metavar='batch.tar.xz',
        help='',
    )

    parser.add_argument(
        'query_fn',
        metavar='annotated_query.fa',
        help='',
    )

    args = parser.parse_args()
    map_queries_to_batch(args.batch_fn,
                         args.query_fn,
                         minimap_preset=args.minimap_preset,
                         minimap_threads=args.threads,
                         minimap_extra_params=args.extra_params)


if __name__ == "__main__":
    main()
