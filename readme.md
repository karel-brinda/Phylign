# MOF-Search

<!-- vim-markdown-toc GFM -->

* [Introduction](#introduction)
* [Installation](#installation)
  * [Step 1: Installing dependencies](#step-1-installing-dependencies)
  * [Step 2: Cloning the repository](#step-2-cloning-the-repository)
  * [Step 3: Running a simple test](#step-3-running-a-simple-test)
  * [Step 4: Downloading the remaining database files](#step-4-downloading-the-remaining-database-files)
* [Usage](#usage)
  * [Running](#running)
  * [Commands](#commands)
  * [Running on a cluster](#running-on-a-cluster)
    * [LSF](#lsf)
* [Files and outputs](#files-and-outputs)
  * [Directories](#directories)
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
```
    conda install -y python>=3.7 snakemake>=6.2.0 mamba>=0.20.0
```


### Step 2: Cloning the repository

**Quick example:**

```
   git clone --recursive https://github.com/karel-brinda/mof-search
   cd mof-search
```

### Step 3: Running a simple test

Run `make test` to ensure the pipeline works for the sample queries and just
   3 batches. This will also setup `COBS`;

`make test` should return 0 (success) and you should have the following
message at the end of the execution, to ensure the test produced the expected
output:
```
   Files output/backbone19Kbp___ecoli_reads_1___ecoli_reads_2___gc01_1kl.sam_summary.xz and data/backbone19Kbp___ecoli_reads_1___ecoli_reads_2___gc01_1kl.sam_summary.xz are identical
```

If the test did not produce the expected output and you obtained an error message such as
```
   Files output/backbone19Kbp___ecoli_reads_1___ecoli_reads_2___gc01_1kl.sam_summary.xz and data/backbone19Kbp.fa differ make: *** [Makefile:21: test] Error 1
```
you should verify why.


### Step 4: Downloading the remaining database files

Run `make download` to download all the remaining assemblies and COBS *k*-mer
indexes for the 661k-HQ collection.


## Usage

### Running

This is our recommended steps to run `mof-search`:

1. Run `make clean` to clean the intermediate files from the previous run;
2. Add your desired queries to the `queries` directory and remove the sample
   ones;
3. Run `make` to run align your queries to the 661k.


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

### Running on a cluster

Running on a cluster is much faster as the jobs produced by this pipeline are quite light and usually start running as
soon as they are scheduled.

#### LSF

1. Test if the pipeline is working on a LSF cluster: `make cluster_lsf_test`;
2. Configure you queries and run the full pipeline: `make cluster_lsf`;



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



## Known limitations


* All methods rely on the ACGT alphabet, and all non-`ACGT` characters in your query files are transformed into `A`.

* When the number of queries is too high, the auxiliary Python scripts start to use too much memory, which may result in swapping. Try to keep the number of queries moderate and ideally their names short. If you have tens or hundreds or more query files, concatenate them all into one before running `mof-search`.

* All query names have to be unique among all query files.



## Contacts

[Karel Brinda](http://karel-brinda.github.io) \<karel.brinda@inria.fr\>

[Leandro Lima](https://github.com/leoisl) \<leandro@ebi.ac.uk\>
