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
    parser.add_argument(
        '--benchmark',
        action="store_true",
        default=False,
        help=
        'Whether to benchmark or just run the command (easier to configure the Snakefile with this).'
    )
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
    if args.benchmark:
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
        benchmark_command = f'{time_command} -a -o {log_file} -f "%e %S %U %P %M %I %O"'
    else:
        benchmark_command = ""

    subprocess.check_call(f'{benchmark_command} {args.command}', shell=True)


if __name__ == "__main__":
    main()
