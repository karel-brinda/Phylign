#!/usr/bin/env python3
import yaml
import sys

with open("config.yaml", "r") as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

# check if cobs_threads is an int
try:
    int(config["cobs_threads"])
except ValueError:
    print("ERROR: to run mof-search in cluster mode, the parameter cobs_threads in config.yaml MUST BE SET to a fixed "
          "int value. Aborting.", file=sys.stderr)
    sys.exit(1)