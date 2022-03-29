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

# ./scripts/batch_align.py asms/chlamydia_pecorum__01.tar.xz ./intermediate/02_filter/gc01_1kl.fa

logging.basicConfig(
    stream=sys.stderr,
    #level=logging.DEBUG,
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


def _write_to_file(fn, fa):
    #print("aaaa", file=sys.stderr)
    logging.debug(f"Opening fasta file {fn}")
    #print("bbb", file=sys.stderr)
    with open(fn, 'wb', 10**8) as fo:
        logging.debug(f"Writing to fasta file {fn}")
        #print("ccc", file=sys.stderr)
        fo.write(fa)
        #print("ddd", file=sys.stderr)


#from signal import signal, SIGPIPE, SIG_DFL
#signal(SIGPIPE, SIG_DFL)


def _check_fifo(fn):
    fifo_mode = stat.S_ISFIFO(os.stat(fn).st_mode)
    logging.debug(f"Checking the FIFO mode of '{fn}': {fifo_mode}")


def minimap2_5(rfa, qfa, minimap_preset):
    """Like minimap2_4, but run as a separate thread with a timeout
    """
    #t = threading.Thread(target=minimap2_4, args=(rfa, qfa, minimap_preset))
    #t.start()
    #t.join(2)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(minimap2_4, rfa, qfa, minimap_preset)
        return_value = future.result(2)
        return return_value


def minimap2_4(rfa, qfa, minimap_preset):
    logging.debug(f"Going to run minimap with the following sequences:")
    logging.debug(f"   rfa: {rfa}")
    logging.debug(f"   qfa: {qfa}")

    with named_pipe() as rfn:
        with named_pipe() as qfn:
            command = [
                "minimap2", "-a", "--eqx", "-x", minimap_preset, rfn, qfn
            ]
            logging.info(f"Running command: {command}")
            with Popen(command, stdout=PIPE) as p:
                logging.info(f"Popen opened, creating fasta writing threads")
                #logging.info(f"Popen opened, creating a thread pool executor")
                #with ProcessPoolExecutor(max_workers=3) as executor:
                #with concurrent.futures.ProcesProcessPoolExecutor() as executor:

                _check_fifo(rfn)
                rf_t = threading.Thread(target=_write_to_file, args=(rfn, rfa))
                rf_t.daemon = True
                rf_t.start()
                #executor.submit(_write_to_file,rfn, rfa)
                #_write_to_file(rfn, rfa)

                _check_fifo(qfn)
                qf_t = threading.Thread(target=_write_to_file,
                                        args=(qfn, str.encode(qfa)))
                qf_t.daemon = True
                qf_t.start()
                #executor.submit(_write_to_file,qfn, str.encode(qfa))
                #_write_to_file(qfn, str.encode(qfa))

                logging.info(f"Running p.communicate")

                output = p.communicate(timeout=2)[0]
                rf_t.join(2)
                qf_t.join(2)
                return output.decode("utf-8")


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


def map_queries_to_batch(asms_fn, query_fn, minimap_preset):
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
        result = minimap2_5(rfa, "\n".join(qfas), minimap_preset)
        assert result and result[0]=="@", f"Output of Minimap2 is empty ('{result}')"
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
                         minimap_preset=args.minimap_preset)


if __name__ == "__main__":
    main()
