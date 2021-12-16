#! /usr/bin/env bash

set -e
set -o pipefail
set -u
#set -f

readonly PROGNAME=$(basename $0)
readonly PROGDIR=$(dirname $0)
readonly -a ARGS=("$@")
readonly NARGS="$#"

if [[ $NARGS -ne 2 ]]; then
	>&2 echo "usage: $PROGNAME index.cobs seqs.fa"
	exit 1
fi

x="$1"
y="$2"

docker run leandroishilima/cobs:1915fc query \
	-i "$x" \
	-f "$y"

