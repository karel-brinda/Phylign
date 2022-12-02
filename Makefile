.PHONY: all test help clean cleanall cluster download match map format report viewconf conda

SHELL=/usr/bin/env bash -eo pipefail
DATETIME=$(shell date -u +"%Y_%m_%dT%H_%M_%S")

.SECONDARY:

.SUFFIXES:

THREADS=$(shell grep "^threads:" config.yaml | awk '{print $$2}')
MAX_DOWNLOAD_THREADS=$(shell grep "^max_download_threads" config.yaml | awk '{print $$2}')
MAX_IO_HEAVY_THREADS=$(shell grep "^max_io_heavy_threads" config.yaml | awk '{print $$2}')
MAX_RAM_MB=$(shell grep "^max_ram_gb:" config.yaml | awk '{print $$2*1024}')
SMK_PARAMS=--jobs ${THREADS} --rerun-incomplete --printshellcmds --keep-going --use-conda --resources max_download_threads=$(MAX_DOWNLOAD_THREADS) max_io_heavy_threads=$(MAX_IO_HEAVY_THREADS) max_ram_mb=$(MAX_RAM_MB)

all: ## Run everything
	make download
	make match
	make map

test: ## Run everything but just with 3 batches to test full pipeline
	snakemake $(SMK_PARAMS) -j 99999 --config batches=data/batches_small.txt -- download  # download is not benchmarked
	scripts/benchmark.py --log logs/benchmarks/test_match_$(DATETIME).txt "snakemake $(SMK_PARAMS) --config batches=data/batches_small.txt nb_best_hits=1 -- match"
	scripts/benchmark.py --log logs/benchmarks/test_map_$(DATETIME).txt   "snakemake $(SMK_PARAMS) --config batches=data/batches_small.txt nb_best_hits=1 -- map"
	diff -s <(xzcat output/reads_1___reads_2___reads_3___reads_4.sam_summary.xz | cut -f -3) <(xzcat data/reads_1___reads_2___reads_3___reads_4.sam_summary.xz  | cut -f -3)

download: ## Download the 661k assemblies and COBS indexes, not benchmarked
	snakemake $(SMK_PARAMS) -j 99999 -- download

match: ## Match queries using COBS (queries -> candidates)
	scripts/benchmark.py --log logs/benchmarks/match_$(DATETIME).txt "snakemake $(SMK_PARAMS) -- match"

map: ## Map candidates to assemblies (candidates -> alignments)
	scripts/benchmark.py --log logs/benchmarks/map_$(DATETIME).txt   "snakemake $(SMK_PARAMS) -- map"

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
	rm -fv output/*
	mkdir -p .snakemake/old_log
	mv .snakemake/log/*.log .snakemake/old_log/ || true

cleanall: clean ## Clean all generated and downloaded files
	rm -f {asms,cobs}/*.xz{,.tmp}

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
		| grep --color='auto' -E '.*\:'
	@#| grep -Ev ^$$

conda: ## Create the conda environments
	snakemake $(SMK_PARAMS) --conda-create-envs-only
