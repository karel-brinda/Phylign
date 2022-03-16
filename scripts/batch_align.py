#! /usr/bin/env python3

import argparse
import atexit
import collections
import os
import re
import sys
import tarfile

from xopen import xopen

from pathlib import Path
from xopen import xopen
from pprint import pprint


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
    print(f"Opening {asms_fn}", file=sys.stderr)
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
            qname_to_qfa[qname] = f"{qname}\n{qseq}\n"
            rnames = qcom.split(",")
            for rname in rnames:
                rname_to_qnames[rname].append(qname)
    return qname_to_qfa, rname_to_qnames


def minimap2(rfa, qfa):
    print(rfa, qfa)
    pass


def map_queries_to_batch(asms_fn, query_fn):
    qname_to_qfa, rname_to_qnames = load_qdicts(query_fn)

    selected_rnames = set([x for x in rname_to_qnames])
    for rname, rfa in iterate_over_batch(asms_fn, selected_rnames):
        qfas = []
        for qname in rname_to_qnames[rname]:
            qfa = qname_to_qfa[qname]
            qfas.append(qfa)
        result = minimap2(rfa, "".join(qfas))
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
    map_queries_to_batch(args.batch_fn, args.query_fn)


if __name__ == "__main__":
    main()
