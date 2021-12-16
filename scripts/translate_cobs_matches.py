#! /usr/bin/env python3

import argparse
import collections
import os
import re
import sys

from xopen import xopen


def translate(matches_fn, transl_fn):
    qname = None
    print("Loading translation dictionary", file=sys.stderr)
    d = _load_transl_dict(transl_fn)
    print("Translating matches", file=sys.stderr)
    with xopen(matches_fn) as f:
        for x in f:
            x = x.strip()
            if not x:
                continue
            if x[0] == "*":
                parts = x[1:].split()
                qname = parts[0]
                nmatches = int(parts[-1])
                if nmatches == 0:
                    print("NA", qname, 0, sep="\t")
            else:
                rid, kmers = x.split()
                ref = d[rid]
                print(ref, qname, kmers, sep="\t")


def _load_transl_dict(transl_fn):
    d = {}
    with xopen(transl_fn) as f:
        for x in f:
            a, b = x.strip().split()
            d[a] = b
    return d


def main():
    parser = argparse.ArgumentParser(description="")

    parser.add_argument(
        'matches',
        metavar='matches.txt.xz',
        help='',
    )

    parser.add_argument(
        'transl',
        metavar='name_translation.tsv.xz',
        help='',
    )

    args = parser.parse_args()

    translate(args.matches, args.transl)


if __name__ == "__main__":
    main()
