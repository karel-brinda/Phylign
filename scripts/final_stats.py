#! /usr/bin/env python3

import argparse
import collections
import lzma
import os
import re
import sys

from pathlib import Path
from xopen import xopen
from pprint import pprint


def _get_batch_name(st):
    assert st[:2] == "=="
    assert st[-2:] == "=="
    x = st.replace("==> ", "").replace(" <==", "")
    b = os.path.basename(x).split("____")[0]
    return b


def get_match(st):
    #print(st)
    p = st.split("\t")
    qname = p[0]
    rname = p[2]
    if rname == "*":
        return qname, None, None
    else:
        accession, contig = rname.split(".")
        return qname, accession, contig


def load_query_names(queries_fn):
    qnames = set()
    with open(queries_fn) as f:
        for x in f:
            if len(x) == 0 or (x[0] != "@" and x[0] != ">"):
                continue
            qname = x.strip().split(" ")[0]
            qnames.add(qname)
    return qnames


def compute_stats(results_fn, queries_fn):
    batches = set()
    refs = set()
    queries_matched = set()
    queries_aligned = set()
    query_ref_pairs = set()

    if queries_fn is not None:
        queries = load_query_names(queries_fn)
    else:
        queries = None

    batch = None

    nb_alignments = 0
    nb_nonalignments = 0

    with lzma.open(results_fn) as fo:
        for x in fo:
            x = x.decode().strip()
            # 1) empty line
            if not x:
                continue
            # 2) header
            if x[:2] == "==":
                b = _get_batch_name(x)
                print(b, "", file=sys.stderr)
            # 3) content line
            else:
                qname, accession, contig = get_match(x)
                queries_matched.add(qname)
                if accession is not None:  # a) alignment
                    queries_aligned.add(qname)
                    nb_alignments += 1
                    batches.add(batch)
                    refs.add(accession)
                    query_ref_pairs.add(f"{accession}__{qname}")
                else:  # b) unaligned
                    nb_nonalignments += 1
    print(file=sys.stderr)
    print("alignments", nb_alignments, sep="\t")
    print("nonalignments", nb_nonalignments, sep="\t")
    if queries is not None:
        print("queries", len(queries), sep="\t")
    print("queries_matched", len(queries_matched), sep="\t")
    print("queries_aligned", len(queries_aligned), sep="\t")
    print("refs", len(refs), sep="\t")
    print("queryref_pairs", len(query_ref_pairs), sep="\t")


def main():

    parser = argparse.ArgumentParser(description="")

    parser.add_argument(
        'queries_fn',
        metavar='queries.fa',
        help='',
    )

    parser.add_argument(
        'results_fn',
        metavar='results.sam_summary.xz',
        help='',
    )

    args = parser.parse_args()

    compute_stats(args.results_fn, args.queries_fn)


if __name__ == "__main__":
    main()
