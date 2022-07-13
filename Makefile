.PHONY: all help clean cleanall cluster download match map format report

SHELL=/usr/bin/env bash -eo pipefail

.SECONDARY:

.SUFFIXES:

DECOMP_THR=$(shell cat config.yaml | yq .decomp_thr)
DOWNLOAD_THR=$(shell cat config.yaml | yq .download_thr)
THR=$(shell cat config.yaml | yq .thr)
SMK_PARAMS=--jobs ${THR} --rerun-incomplete --keep-going --printshellcmds --resources decomp_thr=$(DECOMP_THR) download_thr=$(DOWNLOAD_THR)

all: ## Run everything
	snakemake $(SMK_PARAMS)

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

clean: ## Clean intermediate search files and output
	rm -fv intermediate/*/* output/*

cleanall: clean ## Clean all generated and downloaded files
	rm -f {asms,cobs}/*.xz

cluster: ## Submit to a SLURM cluster
	sbatch \
        -c 10 \
        -p priority \
        --mem=80GB \
        -t 0-08:00:00 \
        --wrap="snakemake --rerun-incomplete -p -j all -k"

