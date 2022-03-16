#! /usr/bin/env python3

import argparse
import atexit
import collections
import os
import re
import sys

from xopen import xopen

from pathlib import Path
from xopen import xopen
from pprint import pprint

KEEP = 100
"""
For every read we want to know top 100 matches

Approach:
    - for every read keep a buffer in memory
    - iterate over all translated cobs outputs
    - keep just top k scores
"""


def cobs_iterator(cobs_matches_fn):
    """Iterator for cobs matches.

    Assumes that cobs ref names start with a random sorting prefix followed by
    an underscore (embedded by Leandro).

    Args:
        cobs_matches_fn (str): File name of cobs output.

    Returns:
        (qname, matches): Qname and list of assignments of the same query, in the form (ref, kmers)

    Todo:
        - if necessary in the future, add batch name from the file name
    """
    qname = None
    matches_buffer = []
    batch = os.path.basename(cobs_matches_fn).split("____")[0]
    print(f"Translating matches {cobs_matches_fn}", file=sys.stderr)
    with xopen(cobs_matches_fn) as f:
        for x in f:
            x = x.strip()
            if not x:
                continue
            if x[0] == "*":
                ## HEADER
                # empty buffer
                if qname is not None:
                    yield qname, batch, matches_buffer
                    matches_buffer = []
                # parse header
                parts = x[1:].split("\t")
                qname = parts[0].split(" ")[0]  # remove fasta comments
                nmatches = int(parts[1])
            else:
                ## MATCH
                tmp_name, kmers = x.split()
                rid, ref = tmp_name.split("_")
                matches_buffer.append((ref, kmers))
    yield qname, batch, matches_buffer


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
        name, seqs, last = last[1:].partition(" ")[0], [], None
        for l in fp:  # read the sequence
            if l[0] in '@+>':
                last = l[:-1]
                break
            seqs.append(l[:-1])
        if not last or last[0] != '+':  # this is a fasta record
            yield name, ''.join(seqs), None  # yield a fasta record
            if not last: break
        else:  # this is a fastq record
            seq, leng, seqs = ''.join(seqs), 0, []
            for l in fp:  # read the quality
                seqs.append(l[:-1])
                leng += len(l) - 1
                if leng >= len(seq):  # have read enough quality
                    last = None
                    yield name, seq, ''.join(seqs)
                    # yield a fastq record
                    break
            if last:  # reach EOF before reading enough quality
                yield name, seq, None  # yield a fasta record instead
                break

def iterate_over_batch(asms_fn):
    pass

def load_qdicts(query_fn):
    with xopen(query_fn) as fo:
        for x in readfq(fo):
            print(x)
    #return qname_to_qfa, rname_to_qname


def minimap2(rfa, qfa):
    pass

def map_queries_to_batch(asms_fn, query_fn):
    qname_to_qfa, rname_to_qname = load_qdicts(query_fn)
    return

    for rname, rfa in iterate_over_batch(asms_fn):
        for qname in rname_to_qname[rname]:
            qfa = rname_to_qfa[qname]
            result=minimap2(rfa, qfa)
            print(result)

def main():

    parser = argparse.ArgumentParser(description="")

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
    map_queries_to_batch(args.batch_fn,args.query_fn)


if __name__ == "__main__":
    main()
