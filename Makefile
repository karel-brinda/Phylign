.PHONY: \
	all test help clean cleanall \
	conda download download_asms download_cobs match map \
	config report \
	cluster_slurm cluster_lsf cluster_lsf_test \
	format checkformat

SHELL=/usr/bin/env bash -eo pipefail
DATETIME=$(shell date -u +"%Y_%m_%dT%H_%M_%S")

.SECONDARY:

.SUFFIXES:

THREADS=$(shell grep "^threads:" config.yaml | awk '{print $$2}')
MAX_DOWNLOAD_THREADS=$(shell grep "^max_download_threads" config.yaml | awk '{print $$2}')
DOWNLOAD_RETRIES=$(shell grep "^download_retries" config.yaml | awk '{print $$2}')
MAX_IO_HEAVY_THREADS=$(shell grep "^max_io_heavy_threads" config.yaml | awk '{print $$2}')
MAX_RAM_MB=$(shell grep "^max_ram_gb:" config.yaml | awk '{print $$2*1024}')

ifeq ($(SMK_CLUSTER_ARGS),)
    # configure local run
    SMK_PARAMS=--cores ${THREADS} --rerun-incomplete --printshellcmds --keep-going --use-conda --resources max_download_threads=$(MAX_DOWNLOAD_THREADS) max_io_heavy_threads=$(MAX_IO_HEAVY_THREADS) max_ram_mb=$(MAX_RAM_MB)
else
    # configure cluster run
    SMK_PARAMS=--cores all --rerun-incomplete --printshellcmds --keep-going --use-conda --resources max_download_threads=10000000 max_io_heavy_threads=10000000 max_ram_mb=1000000000 $(SMK_CLUSTER_ARGS)
endif

DOWNLOAD_PARAMS=--cores $(MAX_DOWNLOAD_THREADS) -j $(MAX_DOWNLOAD_THREADS) --restart-times $(DOWNLOAD_RETRIES)


######################
## General commands ##
######################
all: ## Run everything (the default rule)
	make download
	make match
	make map

DIFF_CMD=diff -q <(gunzip --stdout output/reads_1___reads_2___reads_3___reads_4.sam_summary.gz | cut -f -3) <(xzcat data/reads_1___reads_2___reads_3___reads_4.sam_summary.xz | cut -f -3)

help: ## Print help messages
	@echo -e "$$(grep -hE '^\S*(:.*)?##' $(MAKEFILE_LIST) \
		| sed \
			-e 's/:.*##\s*/:/' \
			-e 's/^\(.*\):\(.*\)/   \\x1b[36m\1\\x1b[m:\2/' \
			-e 's/^\([^#]\)/\1/g' \
			-e 's/: /:/g' \
			-e 's/^#\(.*\)#/\\x1b[90m\1\\x1b[m/' \
		| column -c2 -t -s : )"

clean: ## Clean intermediate search files
	rm -fv intermediate/*/*
	rm -rfv logs
	rm -fv output/*
	mkdir -p .snakemake/old_log
	mv -v .snakemake/log/*.log .snakemake/old_log/ || true

cleanall: clean ## Clean all generated and downloaded files
	rm -f {asms,cobs}/*.xz{,.tmp}

####################
## Pipeline steps ##
####################

conda: ## Create the conda environments
	snakemake $(SMK_PARAMS) --conda-create-envs-only

download: ## Download the assemblies and COBS indexes
	snakemake download $(SMK_PARAMS) $(DOWNLOAD_PARAMS)

download_asms: ## Download only the assemblies
	snakemake download_asms_batches $(SMK_PARAMS) $(DOWNLOAD_PARAMS)

download_cobs: ## Download only the COBS indexes
	snakemake download_cobs_batches $(SMK_PARAMS) $(DOWNLOAD_PARAMS)

match: ## Match queries using COBS (queries -> candidates)
	scripts/benchmark.py --log logs/benchmarks/match_$(DATETIME).txt "snakemake match $(SMK_PARAMS)"

map: ## Map candidates to assemblies (candidates -> alignments)
	scripts/benchmark.py --log logs/benchmarks/map_$(DATETIME).txt   "snakemake map $(SMK_PARAMS)"

###############
## Reporting ##
###############

config: ## Print configuration without comments
	@cat config.yaml \
		| perl -pe 's/ *#.*//g' \
		| grep --color='auto' -E '.*\:'
	@#| grep -Ev ^$$

report: ## Generate Snakemake report
	snakemake --report



#############
## Cluster ##
#############

cluster_slurm: ## Submit to a SLURM cluster
	sbatch \
        -c 10 \
        --mem=80GB \
        -t 0-08:00:00 \
        --wrap="make"

cluster_lsf: ## Submit to LSF cluster
	scripts/check_if_config_is_ok_for_cluster_run.py
	scripts/submit_lsf.sh

cluster_lsf_test: ## Submit the test pipeline to LSF cluster
	scripts/check_if_config_is_ok_for_cluster_run.py
	scripts/submit_lsf.sh test


####################
## For developers ##
####################

format: ## Reformat Python and Snakemake files
	yapf -i */*.py
	snakefmt Snakefile

checkformat: ## Check source code format
	snakefmt --check Snakefile
	yapf --diff */*.py
