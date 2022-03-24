.PHONY: all help clean cleanall cluster download

SHELL=/usr/bin/env bash -eo pipefail

.SECONDARY:

.SUFFIXES:

all: ## Run everything
	snakemake \
		--rerun-incomplete \
		--resources decomp_thr=5 download_thr=5 \
		-p -j all -k

download: ## Download assemblies and cobs indexes
	snakemake \
		--rerun-incomplete \
		-p -j 10 -k download

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

