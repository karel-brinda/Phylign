import os
import time
import sys
from pathlib import Path

log_file = Path(sys.argv[1])
log_file.parent.mkdir(parents=True, exist_ok=True)

initial_RAM = None
max_RAM_usage = 0
while True:
    RAM_usage = int(os.popen('free --bytes').readlines()[1].split()[2])
    RAM_usage = RAM_usage / 1024 / 1024 / 1024
    max_RAM_usage = max(max_RAM_usage, RAM_usage)
    if initial_RAM is None:
        initial_RAM = RAM_usage
    mof_search_RAM_usage = max_RAM_usage - initial_RAM
    with open(log_file, "w", buffering=1024) as fout:
        fout.write(f"Initial RAM usage (GB): {initial_RAM:.2f}\n")
        fout.write(f"Max RAM usage (GB): {max_RAM_usage:.2f}\n")
        fout.write(f"mof-search predicted RAM usage (GB): {mof_search_RAM_usage:.2f}\n")
    time.sleep(0.5)
