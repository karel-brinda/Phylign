# MOF-Search

<!-- vim-markdown-toc GFM -->

* [Introduction](#introduction)
* [Installation](#installation)
  * [Step 1: Installing dependencies](#step-1-installing-dependencies)
  * [Step 2: Cloning the repository](#step-2-cloning-the-repository)
  * [Step 3: Running a simple test](#step-3-running-a-simple-test)
  * [Step 4: Downloading the remaining database files](#step-4-downloading-the-remaining-database-files)
* [Usage](#usage)
  * [Step 1: Provide your queries](#step-1-provide-your-queries)
  * [Step 2: Adjust configuration of your type of search](#step-2-adjust-configuration-of-your-type-of-search)
  * [Step 3: Clean up intermediate files](#step-3-clean-up-intermediate-files)
  * [Step 4: Run the pipeline](#step-4-run-the-pipeline)
  * [Step 5: Analyze your results](#step-5-analyze-your-results)
  * [Commands](#commands)
* [Files and outputs](#files-and-outputs)
  * [Directories](#directories)
* [Running on a cluster](#running-on-a-cluster)
* [Known limitations](#known-limitations)
* [Contacts](#contacts)

<!-- vim-markdown-toc -->


## Introduction

MOF-Search implements BLAST-like search across all pre-2019 bacteria
from ENA (the [661k collection](https://doi.org/10.1371/journal.pbio.3001421)) for standard desktop and laptops computers.


## Installation

### Step 1: Installing dependencies

MOF-Search is implemented as a [Snakemake](https://snakemake.github.io)
pipeline, using the Conda system to manage all non-standard dependencies. To function smoothly, we recommend having Conda with the following packages:


* [Conda](https://docs.conda.io/en/latest/miniconda.html)
* [GNU time](https://www.gnu.org/software/time/) (on Linux present by default, on OS X can be installed by `brew install gnu-time`).
* [Python](https://www.python.org/) (>=3.7)
* [Snakemake](https://snakemake.github.io) (>=6.2.0)
* [Mamba](https://mamba.readthedocs.io/) (>= 0.20.0) - optional, recommended

The last three packages can be installed using Conda by
```bash
    conda install -y python>=3.7 snakemake>=6.2.0 mamba>=0.20.0
```


### Step 2: Cloning the repository

```bash
   git https://github.com/karel-brinda/mof-search
   cd mof-search
```

### Step 3: Running a simple test

Run `make test` to ensure the pipeline works for the sample queries and just
   3 batches. This will also install additional dependencies using Conda or Mamba, such as COBS, SeqTK, and Minimap 2.

**Notes:**
* `make test` should return 0 (success) and you should have the following
message at the end of the execution, to ensure the test produced the expected
output:
  ```bash
     Files output/backbone19Kbp___ecoli_reads_1___ecoli_reads_2___gc01_1kl.sam_summary.xz and data/backbone19Kbp___ecoli_reads_1___ecoli_reads_2___gc01_1kl.sam_summary.xz are identical
  ```

* If the test did not produce the expected output and you obtained an error message such as
  ```bash
     Files output/backbone19Kbp___ecoli_reads_1___ecoli_reads_2___gc01_1kl.sam_summary.xz and data/backbone19Kbp.fa differ make: *** [Makefile:21: test] Error 1
  ```
you should verify why.


### Step 4: Downloading the remaining database files

Run `make download` to download all the remaining assemblies and COBS *k*-mer
indexes for the 661k-HQ collection.


## Usage

### Step 1: Provide your queries

Remove the default test files in the `queries/` directory and copy or symlink
your queries. The supported input formats are FASTA and FASTQ, possibly gzipped.

### Step 2: Adjust configuration of your type of search

Edit the `config.yaml` file. All the options are documented directly there.

### Step 3: Clean up intermediate files

Run `make clean` to clean the intermediate files from the previous runs. This includes COBS matching files, alignments, and various statistics

### Step 4: Run the pipeline

Simply run `make`, which will execute Snakemake with the corresponding parameters. If you want to run the pipeline step by step, run `make match` followed by `make map`.

### Step 5: Analyze your results

Check the output files in `results/`.

If the results don't correspond to what you expected and you need to adjust parameters, go to Step 2. If only the mapping part is to be affected, after changing the configuration, remove only the files in `intermediate/03_map` and `output/` and go directly to Step 4.


### Commands

* `make`            Run everything
* `make test`       Run the queries on 3 batches, to test the pipeline completely
* `make download`   Download the 661k assemblies and COBS indexes
* `make match`      Match queries using COBS (queries -> candidates)
* `make map`        Map candidates to the assemblies (candidates -> alignments)
* `make benchmark`  Benchmarks the pipeline. Benchmark logs are stored in `logs/benchmarks`
* `make report`     Generate Snakemake report
* `make viewconf`   View configuration without comments
* `make conda`      Just create the required `conda` environments
* `make clean`      Clean intermediate search files
* `make cleanall`   Clean all generated and downloaded file



## Files and outputs

### Directories

* `asms/`, `cobs/` Downloaded assemblies and COBS indexes
* `queries/` Queries, to be provided within one or more FASTA files (`.fa`)
* `intermediate/` Intermediate files
   * `00_cobs` Decompressed COBS indexes (tmp)
   * `01_match` COBS matches
   * `02_filter` Filtered candidates
   * `03_map` Minimap2 alignments
   * `fixed_queries` Sanitized queries
* `output/` Results



## Running on a cluster

Running on a cluster is much faster as the jobs produced by this pipeline are quite light and usually start running as
soon as they are scheduled.

**For LSF clusters:**

1. Test if the pipeline is working on a LSF cluster: `make cluster_lsf_test`;
2. Configure you queries and run the full pipeline: `make cluster_lsf`;



## Known limitations


* All methods rely on the ACGT alphabet, and all non-`ACGT` characters in your query files are transformed into `A`.

* When the number of queries is too high, the auxiliary Python scripts start to use too much memory, which may result in swapping. Try to keep the number of queries moderate and ideally their names short. If you have tens or hundreds or more query files, concatenate them all into one before running `mof-search`.

* All query names have to be unique among all query files.



## Contacts

[Karel Brinda](http://karel-brinda.github.io) \<karel.brinda@inria.fr\>

[Leandro Lima](https://github.com/leoisl) \<leandro@ebi.ac.uk\>
