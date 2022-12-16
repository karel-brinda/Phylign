#! /usr/bin/env python3

import argparse
#import atexit
import collections
import concurrent.futures
import logging
import os
import re
import shutil
import shlex
import sys
#import stat
import subprocess
import tarfile
import tempfile
import time
#import threading

from contextlib import contextmanager
from fcntl import fcntl
from pathlib import Path
from pprint import pprint
from select import select
from subprocess import check_output
#from subprocess import PIPE
#from subprocess import Popen
from timeit import default_timer as timer
from xopen import xopen
try:
    from fcntl import F_SETPIPE_SZ
except ImportError:
    # ref: linux uapi/linux/fcntl.h
    F_SETPIPE_SZ = 1024 + 7

# ./scripts/batch_align.py asms/chlamydia_pecorum__01.tar.xz ./intermediate/02_filter/gc01_1kl.fa

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format='[%(asctime)s] (%(levelname)s) %(message)s')


def readfq(fp):
    """Read FASTA/FASTQ file. Based on https://github.com/lh3/readfq/blob/master/readfq.py

    Args:
        fp (file): Input file object.
    """

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
    """Iterate over an xz-compressed TAR file corresponding to a batch with individual FASTA files.

    Args:
        asms_fn (str): xz-compressed TAR file with FASTA files.
        selected_rnames (list): Set of selected FASTA files for which a Minimap instance will be created (note: can contain rnames from other batches).
    Returns:
        (rname (str), rfa (str))
    """
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
                logging.info(f"Skipping {skipped} references in {asms_fn} (no hits for them)")
                skipped = 0
            logging.info(f"Extracting {rname} ({name})")
            f = tar.extractfile(member)
            rfa = f.read()
            yield rname, rfa
    if skipped > 0:
        logging.info(f"Skipping {skipped} references in {asms_fn}")


def load_qdicts(query_fn, accession_fn):
    """Load query dictionaries from the merged & filtered query file.

    Args:
        query_fn (str): Query file.
        accessions_fn (str): File with a list of allowed accessions.

    Returns:
        qname_to_qfa (OrderedDict): qname -> FASTA repr
        rname_to_qnames (dict): rname -> list of queries that should be mapped to this reference
    """
    qname_to_qfa = collections.OrderedDict()

    # STEP 1: Set up dict for accessions
    # all rnames to store, or only some of them?
    #    some -> use dict with restricted keys
    #    all  -> use defaultdict
    # ...rname to be used encoded through key "insertability"
    with open(accession_fn) as f:
        s = f.read().strip()
        accessions = re.split(';|,|\n', s)
        logging.info(f"Loaded ref accesions to consider: {accessions}")
    rname_to_qnames = {}
    for x in accessions:
        rname_to_qnames[x] = []

    # STEP 2: Fill up the query dictionaries
    logging.info(f"Loading query dictionaries (query name -> fasta string, ref_name -> list of cobs-matching queries)")
    with xopen(query_fn) as fo:
        for qname, qcom, qseq, _ in readfq(fo):
            qname_to_qfa[qname] = f">{qname}\n{qseq}"
            if not qcom:  # no refs proposed by COBS for local rnames
                continue
            rnames = qcom.split(",")
            for rname in rnames:
                try:
                    rname_to_qnames[rname].append(qname)
                except KeyError:
                    # batch accession filtering on & not in this batch
                    pass

    # STEP 3: Ensure everything get converted to standard dicts
    logging.info(f"Query dictionaries loaded")
    return qname_to_qfa, rname_to_qnames


@contextmanager
def named_pipe():
    dirname = tempfile.mkdtemp()
    try:
        logging.debug("Creating named pipe...")
        path = os.path.join(dirname, 'named_pipe')
        os.mkfifo(path)
        logging.debug("Named pipe created!")
        yield path
    finally:
        logging.debug("Deleting named pipe...")
        shutil.rmtree(dirname)
        logging.debug("Named pipe deleted!...")


def get_pipe_buffer_size():
    # see https://unix.stackexchange.com/a/11954 for the pipe buffer capacities returned here
    if sys.platform == "linux":
        return 2**20  # 1MB is the max on linux
    elif sys.platform == "darwin":
        return 2**16  # 64KB is the max on darwin
    else:
        raise OSError("Unsupported platform")


def _wait_for_pipe_to_be_ready_to_be_written_to(pipe):
    logging.debug("Waiting for the pipe to be ready to be written to...")
    select([], [pipe], [])
    logging.debug("Ready to write to the pipe!")


def increase_pipe_buffer_size(outstream, buffer_size):
    logging.debug("Setting pipe buffer size...")
    fd = outstream.fileno()
    fcntl(fd, F_SETPIPE_SZ, buffer_size)
    logging.debug("Pipe buffer size increased!")


def _write_to_pipe(pipe_path, data):
    byte_start = 0
    buffer_size = get_pipe_buffer_size()

    logging.debug("Opening pipe for writing...")
    with open(pipe_path, 'wb', buffering=0) as outstream:
        logging.debug("Pipe open for writing!")
        try:
            increase_pipe_buffer_size(outstream, buffer_size)
        except OSError as error:
            logging.error("Failed to set pipe buffer size: " + str(error))
            sys.exit(1)

        logging.debug("Starting to send data to pipe...")
        while byte_start < len(data):
            try:
                chunk_to_write = data[byte_start:byte_start + buffer_size]

                _wait_for_pipe_to_be_ready_to_be_written_to(outstream)

                # Note: this can throw BrokenPipeError if there is no process (i.e. minimap2) reading from the pipe
                logging.debug(f"Writing to pipe...")
                bytes_written = outstream.write(chunk_to_write)
                byte_start += bytes_written
                logging.debug(f"Wrote {bytes_written} bytes to pipe!")

                pipe_buffer_shrunk = bytes_written == 0
                if pipe_buffer_shrunk:
                    buffer_size = buffer_size // 2  # let's reduce the amount we write
                    buffer_size = max(buffer_size, 8)  # we should be able to write at least 8 bytes
                    logging.debug(f"Reduced pipe buffer size to {buffer_size}")

            except BrokenPipeError:
                logging.debug(f"Pipe is broken, waiting for minimap2...")
                time.sleep(0.1)  # waits minimap2 to get the stream


def run_minimap2(command, qfa, timeout=None):
    logging.debug(f"Running command: {command}")
    output = subprocess.check_output(command,
                                     input=qfa,
                                     universal_newlines=True,
                                     stderr=subprocess.DEVNULL,
                                     timeout=timeout)
    assert output and output[0] == "@", f"Output of Minimap2 is empty or corrupted ('{output}')"
    output_lines = output.splitlines()
    output_lines = list(filter(lambda line: not line.startswith("@"), output_lines))
    output_lines = list(filter(lambda line: len(line.strip()), output_lines))
    logging.debug(f"Finished command: {command}")
    return output_lines


def minimap2_4(rfa, qfa, minimap_preset, minimap_threads, minimap_extra_params):
    logging.debug(f"Running minimap2...")

    with named_pipe() as rfn:
        command = [
            "minimap2", "-a", "-x", minimap_preset, "-t",
            str(minimap_threads), *(shlex.split(minimap_extra_params)), rfn, '-'
        ]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # we first get minimap2 up and reading from the pipe
            minimap_2_output = executor.submit(run_minimap2, command, qfa, 5)

            logging.debug("Checking if minimap2 started...")
            while not minimap_2_output.running():
                logging.debug("minimap2 did not start yet, waiting...")
                time.sleep(0.1)
            logging.debug("minimap2 started!")

            # and now we write to the pipe
            logging.debug("Going to write to pipe...")
            _write_to_pipe(rfn, rfa)
            logging.debug("All data written to pipe!")

            return minimap_2_output.result(timeout=5)


def minimap2_using_disk(rfa, qfa, minimap_preset, minimap_threads, minimap_extra_params):
    logging.debug(f"Running minimap2 with disk...")
    with tempfile.NamedTemporaryFile(mode='wb', suffix=".fa", prefix="mof", delete=True) as ref_fh:
        logging.debug(f"Writing data to temp file...")
        ref_fh.write(rfa)
        ref_fh.flush()  # ensure data is written to the file before is read by minimap2

        ref_filepath = ref_fh.name
        command = [
            "minimap2", "-a", "-x", minimap_preset, "-t",
            str(minimap_threads), *(shlex.split(minimap_extra_params)), ref_filepath, '-'
        ]
        return run_minimap2(command, qfa)


def minimap_wrapper(rfa, qfa, minimap_preset, minimap_threads, minimap_extra_params, prefer_pipe):
    if prefer_pipe:
        try:
            return minimap2_4(rfa, qfa, minimap_preset, minimap_threads, minimap_extra_params)
        except (concurrent.futures.TimeoutError, subprocess.TimeoutExpired):
            logging.warning("Minimap2 timed out, using disk")
            return minimap2_using_disk(rfa, qfa, minimap_preset, minimap_threads, minimap_extra_params)
    else:
        return minimap2_using_disk(rfa, qfa, minimap_preset, minimap_threads, minimap_extra_params)


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
                    command = ["minimap2", "-a", "--eqx", "-x", minimap_preset, rfn.name, qfn.name]
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
                command = ["minimap2", "-a", "--eqx", "-x", minimap_preset, rfile.name, qfile.name]
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


def map_queries_to_batch(asms_fn, query_fn, minimap_preset, minimap_threads, minimap_extra_params, prefer_pipe,
                         accessions_fn):
    """Map queries to a batch.

    Args:
        asms_fn (str): Batch .tar.xz file with batch FASTA files.
        query_fn (str): Filtered & merged query FASTA file.
        minimap_preset (str): Minimap preset.
        minimap_threads (int): Nb of minimap threads.
        minimap_extra_params (str): Additional minimap parameters.
        prefer_pipe (bool): Prefer using pipes.
        accessions_fn (str): List of allowed accessions.
    """
    sstart = timer()
    logging.info(f"Mapping queries from '{query_fn}' to '{asms_fn}' using Minimap2 with the '{minimap_preset}' preset")

    # STEP 1: Set up all tables
    #   Load query dictionaries (ideally restricted to this batch):
    #     qname_to_qfa:     query name -> FASTA string
    #     rname_to_qnames:  ref name   -> list of its COBS candidates"
    #   Extract the relevant subset of rnames - rnames_local_subset
    qname_to_qfa, rname_to_qnames = load_qdicts(query_fn, accessions_fn)

    nsr = len(rname_to_qnames)
    logging.debug(f"Identifying filtered rnames in the query file - #{nsr} records: {rname_to_qnames.keys()}")
    naligns_total = 0
    nrefs = 0
    refs = set()
    logging.info(f"Starting the alignment loop")

    # STEP 2: Iterate over compressed assemblies: (ref name, ref FASTA)
    #   Here it's already restricted only to the references proposed by COBS, i.e, hot candidates
    for i, (rname, rfa) in enumerate(iterate_over_batch(asms_fn, rname_to_qnames.keys()), 1):
        start = timer()
        refs.add(rname)

        # STEP 2a: identify queries that are to be mapped to this reference (i.e., rname, rfa)
        qfas = []
        qnames = []
        for qname in rname_to_qnames[rname]:
            qnames.append(qname)
            qfa = qname_to_qfa[qname]
            qfas.append(qfa)

        # STEP 2b: Create a Minimap instance, pass all the data, and get the output lines
        logging.info(f"Minimapping to {rname} (#{i}): {', '.join(qnames)}")
        mm_output_lines = minimap_wrapper(rfa, "\n".join(qfas), minimap_preset, minimap_threads, minimap_extra_params,
                                          prefer_pipe)
        logging.debug("minimap2 finished successfully!")

        # STEP 2c: Print Minimap output
        naligns = len(mm_output_lines)
        minimap_output_is_empty = naligns == 0
        if not minimap_output_is_empty:
            mm_output_str = "\n".join(mm_output_lines)
            print(mm_output_str)

        # STEP 2d: Update & report stats
        naligns_total += naligns
        end = timer()
        s = round(1000 * (end - start)) / 1000.0
        n_q = len(qnames)
        logging.info(f"Computed {naligns} alignments of {n_q} queries to {rname} in {s} seconds")

    # STEP 3: Update & report the final stats
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
        '--pipe',
        action="store_true",
        default=False,
        help='Prefer using pipe instead of disk when communicating with minimap2',
    )

    parser.add_argument(
        '--accessions',
        default=None,
        help='Restrict to a list of accesions (e.g., from a single batch)',
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
                         minimap_extra_params=args.extra_params,
                         prefer_pipe=args.pipe,
                         accessions_fn=args.accessions)


if __name__ == "__main__":
    main()
