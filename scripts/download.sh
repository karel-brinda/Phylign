#! /usr/bin/env bash

set -e
set -o pipefail
set -u
#set -f

readonly PROGNAME=$(basename $0)
readonly PROGDIR=$(dirname $0)
readonly -a ARGS=("$@")
readonly NARGS="$#"

if [[ $NARGS -ne 3 ]]; then
	>&2 echo "Download an xz file with a specificed delay and then verify its consistency"
	>&2 echo
	>&2 echo "usage: $PROGNAME url output_file sleep_time"
	exit 1
fi

url="$1"
output="$2"
sleep_amount="$3"

if [[ "$sleep_amount" -ne 0 ]]; then
	2>&1 echo "Detected previous failed downloads, probably Zenodo blocking downloads."
	2>&1 echo "Now random sleeping for $sleep_amount seconds before retrying..."
	sleep "$sleep_amount"
	2>&1 echo "Retrying..."
fi
2>&1 echo "Downloading $url to ${output}"
curl -s -L "${url}"  > "${output}"
"$PROGDIR/test_xz.py" "${output}"
2>&1 echo "Verified that ${output} is consistent as an xz file"
