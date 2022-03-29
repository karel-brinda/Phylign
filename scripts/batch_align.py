#! /usr/bin/env python3

import argparse
import atexit
import collections
import logging
import os
import re
import sys
import subprocess
import tarfile
import tempfile

from contextlib import contextmanager
from pathlib import Path
from pprint import pprint
from subprocess import check_output
from subprocess import PIPE
from subprocess import Popen
from xopen import xopen

# ./scripts/batch_align.py asms/chlamydia_pecorum__01.tar.xz ./intermediate/02_filter/gc01_1kl.fa

logging.basicConfig(stream=sys.stderr,
                    level=logging.DEBUG,
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
    with tarfile.open(asms_fn, mode="r:xz") as tar:
        for member in tar.getmembers():
            name = member.name
            rname = Path(name).stem
            #print("name",name)
            #print("rname",rname)
            if rname not in selected_rnames:
                continue
            f = tar.extractfile(member)
            rfa = f.read()
            #print(rfa)
            print(f"Extracting {rname} ({name})", file=sys.stderr)
            yield rname, rfa


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




def minimap2_3(rfa, qfa, minimap_preset):
    logging.debug(f"Running minimap with the following sequences:")
    logging.debug(f"   rfa: {rfa}")
    logging.debug(f"   qfa: {qfa}")

    tmpdir = tempfile.mkdtemp()
    rfn = os.path.join(tmpdir, 'ref.fa')
    qfn = os.path.join(tmpdir, 'query.fa')
    logging.debug(f"Opening ref fasta")
    with open(rfn, "wb") as rfo:
        logging.debug(f"Opening query fasta")
        with open(qfn, "w") as qfo:
            logging.debug(f"Writing ref fasta")
            rfo.write(rfa)
            logging.debug(f"Writing query fasta")
            qfo.write(qfa)
    command = [
        "minimap2", "-a", "--eqx", "-x", minimap_preset, rfn, qfn
    ]
    logging.info(f"Running command: {command}")
    output = check_output(command)
    logging.info(f"Cleaning {tmpdir}")
    os.unlink(rnf)  # Remove file
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


def map_queries_to_batch(asms_fn, query_fn, minimap_preset):
    logging.info(
        f"Mapping queries from '{query_fn}' to '{asms_fn}' using Minimap2 with the '{minimap_preset}' preset"
    )
    qname_to_qfa, rname_to_qnames = load_qdicts(query_fn)

    selected_rnames = set([x for x in rname_to_qnames])
    nsr = len(selected_rnames)
    logging.debug(
        f"Identifying rnames in the query file - #{nsr} records: {selected_rnames}"
    )
    for rname, rfa in iterate_over_batch(asms_fn, selected_rnames):
        logging.info(f"Iterating over {rname}")
        qfas = []
        for qname in rname_to_qnames[rname]:
            logging.debug(f"Querying {qname}")
            qfa = qname_to_qfa[qname]
            qfas.append(qfa)
        result = minimap2_3(rfa, "\n".join(qfas), minimap_preset)
        logging.debug(f"Minimap result: {result}")
        print(result, end="")


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
