#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import subprocess


def get_args():
    parser = argparse.ArgumentParser(description='Benchmark a command.')
    parser.add_argument('command',
                        type=str,
                        help='The command to be benchmarked')
    parser.add_argument('--log',
                        type=str,
                        required=True,
                        help='Path to the log file with benchmark statistics.')
    args = parser.parse_args()
    return args


def get_time_command():
    if sys.platform == "linux":
        time_command = "/usr/bin/time"
    elif sys.platform == "darwin":
        time_command = "gtime"
    else:
        raise Exception("Unsupported OS")
    return time_command


def main():
    args = get_args()
    log_file = Path(args.log)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w") as log_fh:
        print(f"Benchmarking command: {args.command}", file=log_fh)
        header = [
            "real(s)", "sys(s)", "user(s)", "percent_CPU", "max_RAM(kb)",
            "FS_inputs", "FS_outputs"
        ]
        print(" ".join(header), file=log_fh)

    time_command = get_time_command()
    subprocess.check_call(
        f'{time_command} -a -o {log_file} -f "%e %S %U %P %M %I %O" {args.command}',
        shell=True)


if __name__ == "__main__":
    main()
