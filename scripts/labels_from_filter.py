#! /usr/bin/env python3

import argparse
import os
import sys
import json

from pathlib import Path
from collections import defaultdict, Counter


def get_labels_by_sampleid(path_to_labels,):
    """
    return a dictionary with (sampleid,label) pair values
    from data/labels_krakenbracken_by_sampleid.txt
    """
    labels_by_sampleid = defaultdict(str)
    with open(path_to_labels, "r") as fp:
        
        for line in fp.readlines():
            sampleid, label = line.replace("\n","").split("\t")
            labels_by_sampleid[sampleid] = label
    
    return labels_by_sampleid


def get_hits_by_query(path_to_hits,):
    """
    return a tuple with the query id and the sampleid of the best hits
    from intermediate/04_filter/all_queries.fa

    Since some short queries can retrieve more hits than desired (due to be equally ranked)
    the 'max_hits' parameters is defined to create a consistent CSV
    """
    hits_by_queryid = defaultdict(list)
    with open(path_to_hits, "r") as fp:
        
        for line in fp.readlines():
            if line.startswith(">"):
                line = line.replace(">","").replace("\n","").strip()
                try:
                    sampleid, hits, *_ = line.strip().split(" ")
                    hits_by_queryid[sampleid] = hits.split(",")
                except:
                    sampleid= line
                    hits_by_queryid[sampleid] = []
    
    return hits_by_queryid

def dict2csv(_dict, path_save, max_hits=10) ->  None:
    import csv

    # open the file in the write mode
    with open(path_save, 'w') as f:
        # create the csv writer
        writer = csv.writer(f,)

        # write a row to the csv file
        for k,v in _dict.items():
            row = [k]
            row.extend(v)#[:max_hits])            
            writer.writerow(row)


def get_queryid_by_input(path_preprocessed="intermediate/00_queries_preprocessed"):
    """
    link each query sequence to its assembly    
    
    (1) from input/ get the list of queryid of each assembly (i.e. id of its contigs)
    (2) then 
    """
    queryid_by_input = defaultdict(list)
    for path in Path(path_preprocessed).rglob(f"*.fa"):
        _input = path.stem
        with open(path,"r") as fp:
            for line in fp.readlines():
                if line.startswith(">"):
                    queryid = line.replace(">","").split(" ")[0].strip()
                    queryid_by_input[_input].append(queryid)

    return queryid_by_input

def label_consensus(hits_by_queryid, labels_by_queryid, method="majority"):
    pass

def main():

    parser = argparse.ArgumentParser(description="Label query assembly from COBS match")

    parser.add_argument(
        '--path-labels',
        help='data/labels_krakenbracken_by_sampleid.txt',
        dest="path_labels",
    )

    parser.add_argument(
        '--path-hits',
        default='intermediate/04_filter/all_queries.fa',
        dest="path_hits",
    )

    parser.add_argument(
        '--path-preprocessed',
        default='intermediate/00_queries_preprocessed',
        dest="path_preprocessed",
    )

    parser.add_argument(
        '--outdir',
        help='',
        dest="outdir",
    )
    
    args = parser.parse_args()

    # Load Index Labels
    labels_by_sampleid = get_labels_by_sampleid(args.path_labels) 
    # print(len(labels_by_sampleid))

    # Get best hits (sampleid)
    hits_by_queryid = get_hits_by_query(args.path_hits)

    # Map best hits (sampleid) to its labels
    labels_by_queryid = {queryid: [labels_by_sampleid[hit] for hit in hits] for queryid, hits in hits_by_queryid.items()} 
    # print(labels_by_queryid)

    Path(args.outdir).mkdir(exist_ok=True,parents=True)
    dict2csv(labels_by_queryid, Path(args.outdir).joinpath("labels_best_hits____all_queries.csv"))
    print(f"Done!, see {args.outdir}")

    queryid_by_input = get_queryid_by_input(path_preprocessed=args.path_preprocessed)

    consensus_label = dict()
    for _input, list_queryid in queryid_by_input.items():

        labels_input = []
        for queryid in list_queryid:
            labels_input.extend(labels_by_queryid[queryid])

        label = Counter(labels_input).most_common()[0][0]
        consensus_label[_input] = label

    print(queryid_by_input)
    with open(Path(args.outdir).joinpath("queryid_by_input____all_queries.json"),"w") as fp:
        json.dump(queryid_by_input, fp, indent=1, ensure_ascii=False)

    with open(Path(args.outdir).joinpath("consensus_label____all_queries.txt"),"w") as fp:
        # 
        for _input, label in consensus_label.items():
            fp.write(f"{_input}\t{label}\n")
        # json.dump(consensus_label, fp, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
