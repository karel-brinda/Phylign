#! /usr/bin/env python3

import argparse
import collections
import os
import re
import sys

from xopen import xopen


def translate(matches_fn):
    qname = None
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
                name, kmers = x.split()
                rid, ref = name.split("_")
                print(ref, qname, kmers, sep="\t")


def main():
    parser = argparse.ArgumentParser(description="")

    parser.add_argument(
        'matches',
        metavar='matches.txt.xz',
        help='',
    )

    args = parser.parse_args()

    translate(args.matches)


if __name__ == "__main__":
    main()
