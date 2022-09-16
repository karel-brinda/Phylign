#!/usr/bin/env bash

# Note: run this script from mof-search root
xz --robot --list cobs/*.cobs_classic.xz |
  grep -v "^totals" |
  awk 'BEGIN{ORS=""}{if(NR%2==1){print $2," "}else{print $5,"\n"}}' \
  > data/decompressed_indexes_sizes.txt
