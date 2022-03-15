#! /usr/bin/env python3

import argparse
import atexit
import collections
import os
import re
import sys

from pathlib import Path
from xopen import xopen
from pprint import pprint


"""
TODO:
    - add filtering so that the number of candidate files is low
    - loads seqs
    - output hierarchy - batch / file; or maybe just batch files to  keep it
    simple and then some piping ot minimap in another script?
       - maybe read name - list of refs?
    - double check that reads are in the right order
    - references don't have to be - we will be just iterating through them and
    side checking dict queries
    - document the assumption that the number of reads is small
"""



KEEP = 100
"""
For every read we want to know top 100 matches

Approach:
    - for every read keep a buffer in memory
    - iterate over all translated cobs outputs
    - keep just top k scores
"""


class Read:
    """A simple optimized buffer for top matches for a single read accross batches. Doesn't know its own read name.
    """

    def __init__(self, keep):
        self._min_matching_kmers = 0  #should be increased once the number of records >keep
        self._matches=[]

    def add_rec(self, batch, sample, kmers):
        self._matches.append((batch, sample, kmers))

    def _sort_and_prune(self):
        ###
        ### TODO: Finish
        ###

        #1. sort
        self._matches.sort(key=lambda x: (x[2], x[0], x[1]))  # todo: function
        #2. identify where to stop
        #3. trim the list
        #4. update _min_kmers_filter according to this value


##
## TODO: add support for empty matches / NA values
##
class BestMatches:
    """Class for all reads.
    """

    def __init__(self, keep):
        self._keep = keep
        self._read_dict = collections.defaultdict(
            lambda: Read(keep=self._keep))
        self._output_fastas = {}
        atexit.register(self._cleanup)

    def _add_rec(self, batch, sample, read, kmers):
        """Process one translated cobs output line.
        """
        self._read_dict[read].add_rec(batch, sample, kmers)

    def process_file(self, fn):
        """Process a translated cobs file.
        """
        with xopen(fn) as fo:
            print(f"Processing {fn}", file=sys.stderr)
            batch, _, _ = Path(fn).name.partition("____")
            #print(batch)
            for x in fo:
                sample, read, kmers = x.strip().split()
                self._add_rec(batch, sample, read, kmers)

    def _print_output_1read(self, rname, best_refs):
        """TODO: Add a buffer of opened files
        """
        for ref in best_refs:
            try:
                self._output_fastas[ref]
            except KeyError:
                self._output_fastas[ref] = open(f"{ref}.fa", "w+")
            self._output_fastas[ref].write(f">{rname}\nAA\n")

    def _cleanup(self):
        for _, fo in self._output_fastas.items() :
            fo.close()

    def print_output(self):
        """Iterate over top matches and print them into FASTA files.
        """
        for rname, read in self._read_dict.items():
            best_refs = [x[1] for x in read._matches]
            self._print_output_1read(rname, best_refs)


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
