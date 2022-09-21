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

DEFAULT_KEEP = 100
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
    print(f"Opening cobs reading iterator for {cobs_matches_fn}",
          file=sys.stderr)
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


def fa_iterator(fn):  # this is a generator function
    with open(fn) as fp:
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


class SingleQuery:
    """A simple optimized buffer for keeping top matches for a single read accross batches.

    Args:
        keep_matches (int): The number of top matches to keep.


    Attributes:
        _matches (list): A list of (ref, kmers)
    """

    def __init__(self, keep_matches):
        self._keep_matches = keep_matches

    def new_query(self, qname, seq):
        self._qname = qname
        self._seq = seq
        self._min_matching_kmers = 0  #should be increased once the number of records >keep
        self._matches = []

    def add_matches(self, batch, matches):
        """Add matches.
        """
        for mtch in matches:
            ref, kmers = mtch
            kmers = int(kmers)
            if kmers >= self._min_matching_kmers:
                self._matches.append((batch, ref, kmers))

    def prune(self):
        # 1. sort and exit if not full
        self._matches.sort(key=lambda x: (-x[2], x[0], x[1]))

        # 2. separate losers
        losers = self._matches[self._keep_matches:]
        self._matches = self._matches[:self._keep_matches]

        # 3. return back tie records from losers
        if losers:
            #get the tie value
            self._min_matching_kmers = self._matches[-1][2]
            for x in losers:
                if x[2] == self._min_matching_kmers:
                    #print(f"Returning {x}", file=sys.stderr)
                    self._matches.append(x)
                else:
                    break

    def get_fasta(self):
        name = self._qname
        com = ",".join([x[1] for x in self._matches])
        seq = self._seq
        return f">{name} {com}\n{seq}"


class Sift:
    """Sifting class for all reported cobs assignments.
    """

    def __init__(self, query_fn, keep_matches, match_fns):
        self._fa_iterator = fa_iterator(query_fn)
        self._cobs_iterators = [cobs_iterator(fn) for fn in match_fns]
        self._keep_matches = keep_matches
        self._single_query = SingleQuery(self._keep_matches)

    def __iter__(self):
        return self

    def __next__(self):
        qname, seq, _ = next(self._fa_iterator)
        self._single_query.new_query(qname, seq)
        for ci in self._cobs_iterators:
            #x=next(ci)
            #print(x)
            qname2, batch, matches = next(ci)
            assert qname == qname2, f"{qname}!={qname2}"
            self._single_query.add_matches(batch, matches)
            self._single_query.prune()
        #self._single_query.prune()
        return qname, self._single_query.get_fasta()

    def process_cobs_file(self, cobs_fn):
        for i, (qname, batch, matches) in enumerate(cobs_iterator(cobs_fn)):
            print(f"Processing batch {batch} query #{i} ({qname})",
                  file=sys.stderr)
            #try:
            #    _ = self._query_dict[qname]
            #except KeyError:
            #    self._query_dict[qname] = SingleQuery(qname, self._keep_matches)
            #print(f"qname {qname} batch {batch} matches {matches}")
            self._query_dict[qname].add_matches(batch, matches)
            #print(qname)


def process_files(query_fn, match_fns, keep_matches):
    sift = Sift(keep_matches=keep_matches,
                query_fn=query_fn,
                match_fns=match_fns)
    for i, (qname, f) in enumerate(sift):
        print(f)


def main():

    parser = argparse.ArgumentParser(description="")

    parser.add_argument(
        'match_fn',
        metavar='',
        nargs='+',
        help='',
    )

    parser.add_argument(
        '-q',
        metavar='str',
        dest='query_fn',
        required=True,
        help=f'query file',
    )

    parser.add_argument(
        '-n',
        metavar='int',
        dest='keep',
        type=int,
        default=DEFAULT_KEEP,
        help=f'no. of best hits to keep [{DEFAULT_KEEP}]',
    )

    args = parser.parse_args()
    process_files(args.query_fn, args.match_fn, args.keep)


if __name__ == "__main__":
    main()
