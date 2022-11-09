#!/usr/bin/env bash
kmer_thres=$1
threads=$2
compressed_cobs_index=$3
uncompressed_batch_size=$4
query=$5

cobs query --load-complete -t ${kmer_thres} -T ${threads} \
  -i <(xzcat --no-sparse --ignore-check "${compressed_cobs_index}") \
  --index-sizes ${uncompressed_batch_size} -f "${query}"
