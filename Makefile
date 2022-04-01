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

download: ## Download assemblies and COBS indexes
	snakemake $(SMK_PARAMS) -- download

match: ## Match queries to the COBS indexes
	snakemake $(SMK_PARAMS) -- match

map: ## Map reads to the assemblies
	snakemake $(SMK_PARAMS) -- map

report: ## Generate Snakemake report
	snakemake --report

format: ## Reformat Python and Snakemake files
	yapf -i */*.py
	snakefmt Snakefile

help: ## Print help message
	@echo "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) | sed -e 's/:.*##\s*/:/' -e 's/^\(.\+\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s : | sort)"

clean: ## Clean
	rm -f intermediate/{01_*,02*,03*,04*}/*.xz

cleanall: clean ## Clean all
	rm -f {asms,cobs}/*.xz

cluster: ## Submit to a SLURM cluster
	sbatch \
        -c 10 \
        -p priority \
        --mem=80GB \
        -t 0-08:00:00 \
        --wrap="snakemake --rerun-incomplete -p -j all -k"

