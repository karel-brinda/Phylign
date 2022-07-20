.PHONY: all test help clean cleanall cluster download match map format report

SHELL=/usr/bin/env bash -eo pipefail

.SECONDARY:

.SUFFIXES:

MAX_DECOMP_JOBS=$(shell grep "^max_decomp_jobs" config.yaml | awk '{print $$2}')
MAX_DOWNLOAD_JOBS=$(shell grep "^max_download_jobs" config.yaml | awk '{print $$2}')
THR=$(shell grep "^thr" config.yaml | awk '{print $$2}')
SMK_PARAMS=--jobs ${THR} --rerun-incomplete --printshellcmds --keep-going --use-conda --resources max_decomp_jobs=$(MAX_DECOMP_JOBS) max_download_jobs=$(MAX_DOWNLOAD_JOBS)

all: ## Run everything
	snakemake $(SMK_PARAMS)

test: ## Run everything but just with 3 batches to test full pipeline
	snakemake $(SMK_PARAMS) --config batches=batches_small.txt

download: ## Download the 661k assemblies and COBS indexes
	snakemake $(SMK_PARAMS) -- download

match: ## Match queries using COBS (queries -> candidates)
	snakemake $(SMK_PARAMS) -- match

map: ## Map candidates to assemblies (candidates -> alignments)
	snakemake $(SMK_PARAMS) -- map

report: ## Generate Snakemake report
	snakemake --report

format: ## Reformat Python and Snakemake files
	yapf -i */*.py
	snakefmt Snakefile

help: ## Print help message
	@echo "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) | sed -e 's/:.*##\s*/:/' -e 's/^\(.\+\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s : | sort)"

clean: ## Clean intermediate search files
	rm -fv intermediate/*/*

cleanall: clean ## Clean all generated and downloaded files
	rm -f {asms,cobs}/*.xz

cluster: ## Submit to a SLURM cluster
	sbatch \
        -c 10 \
        -p priority \
        --mem=80GB \
        -t 0-08:00:00 \
        --wrap="snakemake --rerun-incomplete -p -j all -k"

