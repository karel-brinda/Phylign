#! /usr/bin/env python3

import argparse
import lzma
import os
import sys


def error(*msg):
    print(*msg, file=sys.stderr)


def test_xz(fn):
    code = 0

    s = os.path.getsize(fn)
    if s < 100000:
        error(f"File {fn} is too small, likely corrupted")
        code = 1

    try:
        with lzma.open(fn) as f:
            a = f.read(10)
    except lzma.LZMAError:
        error(f"File {fn} is not a valid xz archive")
        code = 2

    sys.exit(code)


def main():

    parser = argparse.ArgumentParser(description="Test an xz file")

    parser.add_argument(
        'xz',
        metavar='file.xz',
        help='File to test',
    )

    args = parser.parse_args()

    test_xz(args.xz)


if __name__ == "__main__":
    main()
