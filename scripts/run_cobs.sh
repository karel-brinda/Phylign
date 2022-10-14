#!/usr/bin/env bash
kmer_thres=$1
threads=$2
compressed_cobs_index=$3
uncompressed_batch_size=$4
query=$5
nb_best_hits=$6
output=$7

cobs query --load-complete -t ${kmer_thres} -T ${threads} -i <(xzcat "${compressed_cobs_index}") \
  --index-sizes ${uncompressed_batch_size} -f "${query}" \
  | ./scripts/postprocess_cobs.py -n ${nb_best_hits} \
  | gzip > "${output}"
