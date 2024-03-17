#!/usr/bin/env bash

# Note: run this script from Phylign root
xz --robot --list -vv cobs/*.cobs_classic.xz |
  grep -v "^totals" |
  awk 'BEGIN{ORS=""}
  {
    if($1=="name"){
      print $2," "
    }else if ($1=="file"){
      print $5," "
    }else if ($1=="summary"){
      print $2,"\n"
    }
  }' > data/decompressed_indexes_sizes.txt
