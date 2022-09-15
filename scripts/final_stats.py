#! /usr/bin/env python3

import argparse
import lzma
import os
import sys


def readfq(fp):
    """From https://github.com/lh3/readfq/blob/master/readfq.py
    """
    last = None
    while True:
        if not last:
            for l in fp:
                if l[0] in '>@':
                    last = l[:-1]
                    break
        if not last: break
        name, seqs, last = last[1:].partition(" ")[0], [], None
        for l in fp:
            if l[0] in '@+>':
                last = l[:-1]
                break
            seqs.append(l[:-1])
        if not last or last[0] != '+':
            yield name, ''.join(seqs), None
            if not last: break
        else:
            seq, leng, seqs = ''.join(seqs), 0, []
            for l in fp:
                seqs.append(l[:-1])
                leng += len(l) - 1
                if leng >= len(seq):
                    last = None
                    yield name, seq, ''.join(seqs)
                    break
            if last:
                yield name, seq, None
                break


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
        accession, _, contig = rname.partition(".")
        return qname, accession, contig


def load_query_names_and_bps(queries_fn):
    qnames = set()
    bps = 0
    with open(queries_fn) as f:
        for qname, seq, qual in readfq(f):
            qnames.add(qname)
            bps += len(seq)
    return qnames, bps


def compute_stats(results_fn, queries_fn):
    batches = set()
    refs = set()
    queries_matched = set()
    queries_aligned = set()
    query_ref_pairs = set()

    if queries_fn is not None:
        queries, queries_bps = load_query_names_and_bps(queries_fn)
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
                batch = _get_batch_name(x)
                print(batch, "", file=sys.stderr)
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
    #
    if queries is not None:
        print("queries", len(queries), sep="\t")
        print("cumul_length_bps", queries_bps, sep="\t")
        assert queries_matched.issubset(
            queries), f"queries_matched not a subset of queries"
        assert queries_aligned.issubset(
            queries), f"queries_aligned not a subset of queries"
    print("matched_queries", len(queries_matched), sep="\t")
    print("aligned_queries", len(queries_aligned), sep="\t")
    print("aligned_segments", nb_alignments, sep="\t")
    print("distinct_genome_query_pairs", len(query_ref_pairs), sep="\t")
    print("target_genomes", len(refs), sep="\t")
    print("target_batches", len(batches))
    print("nonalignments", nb_nonalignments, sep="\t")


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
