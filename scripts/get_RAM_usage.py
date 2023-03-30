import time
import sys
from pathlib import Path

log_file = Path(sys.argv[1])
log_file.parent.mkdir(parents=True, exist_ok=True)

initial_RAM = None
max_RAM_usage = 0

try:
    import psutil
    while True:
        RAM_usage = psutil.virtual_memory().used
        RAM_usage = RAM_usage / 1024
        max_RAM_usage = max(max_RAM_usage, RAM_usage)
        if initial_RAM is None:
            initial_RAM = RAM_usage
        mof_search_RAM_usage = max_RAM_usage - initial_RAM
        with open(log_file, "w", buffering=1024) as fout:
            fout.write(f"{mof_search_RAM_usage:.2f}")
        time.sleep(0.1)
except ImportError:
    with open(log_file, "w", buffering=1024) as fout:
        fout.write("N/A (psutil not installed)")
