#!/usr/bin/env bash
url=$1
output=$2
sleep_amount=$3

if [ $sleep_amount -gt 0 ]; then
    echo "Detected previous failed downloads, probably Zenodo blocking downloads."
    echo "Now random sleeping for $sleep_amount seconds before retrying..."
    sleep $sleep_amount
    echo "Retrying..."
fi
echo "Downloading $url ..."
curl -s -L "${url}"  > "${output}"
scripts/test_xz.py "${output}"
