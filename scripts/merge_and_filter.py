#! /usr/bin/env python3

import argparse
import collections
import os
import re
import sys

from pathlib import Path
from xopen import xopen
from pprint import pprint

KEEP = 100


class BestMatches:
    def __init__(self, keep):
        self._keep = keep

    def process_file(self, fn):
        pass

    def print_output(self, fn):
        pass


def merge_and_filter(fns, keep):
    bm = BestMatches(keep)
    for fn in fns:
        bm.process_file(fn)
    bm.print_output()


def main():

    parser = argparse.ArgumentParser(description="")

    parser.add_argument(
        'match_fn',
        metavar='',
        nargs='+',
        help='',
    )

    parser.add_argument(
        '-k',
        metavar='int',
        dest='keep',
        default=KEEP,
        help=f'no. of best hits to keep [{KEEP}]',
    )

    args = parser.parse_args()

    merge_and_filter(args.match_fn, args.keep)


if __name__ == "__main__":
    main()
