#! /usr/bin/env python3

import argparse
import collections
import os
import re
import sys


def get_nb_kmers(cobs_line):
    p = cobs_line.split("\t")
    nb_kmers = int(p[-1])
    return nb_kmers


def remove_rnd_id(cobs_line):
    _, _, r = cobs_line.partition("_")
    return "_" + r


def process_cobs_output(hits_to_keep):
    for x in sys.stdin:
        if x[0] == "*":
            i = 0
            print(x, end="")
            min_kmers = 0
        else:
            y = remove_rnd_id(x)
            i += 1

            if i < hits_to_keep:
                print(y, end="")
            elif i == hits_to_keep:
                print(y, end="")
                min_kmers = get_nb_kmers(y)
            else:
                kmers = get_nb_kmers(y)
                if kmers == min_kmers:
                    print(y, end="")


def main():

    parser = argparse.ArgumentParser(
        description="Postprocess cobs output: keep top n hits (+ties) and remove random identifiers")

    parser.add_argument(
        '-n',
        metavar='int',
        dest='keep',
        required=True,
        type=int,
        help=f'no. of best hits to keep',
    )

    args = parser.parse_args()

    process_cobs_output(args.keep)


if __name__ == "__main__":
    main()
