.PHONY: all test help clean cleanall cluster download match map benchmark format report viewconf conda

SHELL=/usr/bin/env bash -eo pipefail
DATETIME=$(shell date -u +"%Y_%m_%dT%H_%M_%S")

.SECONDARY:

.SUFFIXES:

MAX_DECOMP_MB=$(shell grep "^max_decomp_MB" config.yaml | awk '{print $$2}')
MAX_HEAVY_IO_JOBS=$(shell grep "^max_heavy_IO_jobs" config.yaml | awk '{print $$2}')
MAX_DOWNLOAD_JOBS=$(shell grep "^max_download_jobs" config.yaml | awk '{print $$2}')
THR=$(shell grep "^thr" config.yaml | awk '{print $$2}')
SMK_PARAMS=--jobs ${THR} --rerun-incomplete --printshellcmds --keep-going --use-conda --resources max_decomp_MB=$(MAX_DECOMP_MB) max_download_jobs=$(MAX_DOWNLOAD_JOBS) max_heavy_IO_jobs=$(MAX_HEAVY_IO_JOBS)

all: ## Run everything
	snakemake $(SMK_PARAMS)

test: ## Run everything but just with 3 batches to test full pipeline
	snakemake $(SMK_PARAMS) --config batches=batches_small.txt

test_benchmark: ## benchmark the test pipeline. Benchmark logs are stored in logs/benchmarks
	snakemake $(SMK_PARAMS) --config batches=batches_small.txt -- download  # download is not benchmarked
	scripts/benchmark.py --benchmark --log logs/benchmarks/test_match_$(DATETIME).txt "snakemake $(SMK_PARAMS) --config batches=batches_small.txt benchmark=True -- match"
	scripts/benchmark.py --benchmark --log logs/benchmarks/test_map_$(DATETIME).txt   "snakemake $(SMK_PARAMS) --config batches=batches_small.txt benchmark=True -- map"

download: ## Download the 661k assemblies and COBS indexes
	snakemake $(SMK_PARAMS) -j 99999 -- download

match: ## Match queries using COBS (queries -> candidates)
	snakemake $(SMK_PARAMS) -- match

map: ## Map candidates to assemblies (candidates -> alignments)
	snakemake $(SMK_PARAMS) -- map

benchmark: ## benchmark this pipeline. Benchmark logs are stored in logs/benchmarks
	make download  # download is not benchmarked
	scripts/benchmark.py --benchmark --log logs/benchmarks/match_$(DATETIME).txt "snakemake $(SMK_PARAMS) --config benchmark=True -- match"
	scripts/benchmark.py --benchmark --log logs/benchmarks/map_$(DATETIME).txt   "snakemake $(SMK_PARAMS) --config benchmark=True -- map"

report: ## Generate Snakemake report
	snakemake --report

format: ## Reformat Python and Snakemake files
	yapf -i */*.py
	snakefmt Snakefile

help: ## Print help message
	@echo "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) | sed -e 's/:.*##\s*/:/' -e 's/^\(.\+\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s : | sort)"

clean: ## Clean intermediate search files
	rm -fv intermediate/*/*
	rm -rfv logs

cleanall: clean ## Clean all generated and downloaded files
	rm -f {asms,cobs}/*.xz

cluster: ## Submit to a SLURM cluster
	sbatch \
        -c 10 \
        -p priority \
        --mem=80GB \
        -t 0-08:00:00 \
        --wrap="snakemake --rerun-incomplete -p -j all -k"

viewconf: ## View configuration without comments
	@cat config.yaml \
		| perl -pe 's/ *#.*//g' \
		| grep -Ev ^$$

conda: ## Create the conda environments
	snakemake $(SMK_PARAMS) --conda-create-envs-only
