#! /usr/bin/env bash

set -e
set -o pipefail
set -u
#set -f

readonly PROGNAME=$(basename $0)
readonly PROGDIR=$(dirname $0)
readonly -a ARGS=("$@")
readonly NARGS="$#"

i=0
for fn in "$@"
do
	if [[ "$i" -ne "0" ]]; then
		echo
	fi
	echo "==> $fn <=="
	((i=i+1))
	gunzip --stdout "$fn" \
		| grep -Ev "^@"
done

