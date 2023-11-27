#!/usr/bin/env bash

set -e
set -o pipefail
set -u
#set -f

readonly PROGNAME=$(basename $0)
readonly PROGDIR=$(dirname $0)
readonly -a ARGS=("$@")
readonly NARGS="$#"

if [[ $NARGS -ne 5 ]]; then
	>&2 echo "usage: $PROGNAME kmer_thres threads cobs_index.xz uncompressed_size query.fa"
	exit 1
fi

kmer_thres="$1"
threads="$2"
compressed_cobs_index="$3"
uncompressed_batch_size="$4"
query="$5"

cobs query --load-complete \
	-t ${kmer_thres} \
	-T ${threads} \
	-i <(xzcat --no-sparse --ignore-check "${compressed_cobs_index}") \
	--index-sizes ${uncompressed_batch_size} \
	-f "${query}"
