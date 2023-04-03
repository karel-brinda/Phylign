#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import subprocess
import datetime


def get_args():
    parser = argparse.ArgumentParser(description='Benchmark a command.')
    parser.add_argument('command', type=str, help='The command to be benchmarked')
    parser.add_argument('--log', type=str, required=True, help='Path to the log file with benchmark statistics.')
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
    tmp_log_file = Path(f"{log_file}.tmp")
    is_benchmarking_pipeline = args.command.split()[0] == "snakemake"

    with open(log_file, "w") as log_fh:
        formatted_command = " ".join(args.command.replace("\\\n", " ").strip().split())
        print(f"# Benchmarking command: {formatted_command}", file=log_fh)
        header = [
            "real(s)", "sys(s)", "user(s)", "percent_CPU", "max_RAM(kb)", "FS_inputs", "FS_outputs",
            "elapsed_time_alt(s)"
        ]
        if is_benchmarking_pipeline:
            header.append("max_delta_system_RAM(kb)")
        print("\t".join(header), file=log_fh)

    time_command = get_time_command()
    benchmark_command = f'{time_command} -o {tmp_log_file} -f "%e\t%S\t%U\t%P\t%M\t%I\t%O"'

    start_time = datetime.datetime.now()
    main_process = subprocess.Popen(f'{benchmark_command} {args.command}', shell=True)
    if is_benchmarking_pipeline:
        RAM_tmp_log_file = Path(f"{log_file}.RAM.tmp")
        RAM_benchmarking_process = subprocess.Popen([sys.executable, "scripts/get_RAM_usage.py", str(RAM_tmp_log_file),
                                                     str(main_process.pid)])
    return_code = main_process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, main_process.args,
                                 output=main_process.stdout, stderr=main_process.stderr)

    end_time = datetime.datetime.now()
    elapsed_seconds = (end_time - start_time).total_seconds()
    with open(tmp_log_file) as log_fh_tmp, open(log_file, "a") as log_fh:
        log_line = log_fh_tmp.readline().strip()
        log_line += f"\t{elapsed_seconds}"

        if is_benchmarking_pipeline:
            RAM_benchmarking_process.kill()
            with open(RAM_tmp_log_file) as RAM_tmp_log_fh:
                RAM_usage = RAM_tmp_log_fh.readline().strip()
            log_line += f"\t{RAM_usage}"
            RAM_tmp_log_file.unlink()

        print(log_line, file=log_fh)

    tmp_log_file.unlink()


if __name__ == "__main__":
    main()
