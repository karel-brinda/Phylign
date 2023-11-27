# MOF-Search

<p>
<a href="https://brinda.eu/mof">
    <img src="docs/logo_wbg.svg" align="left" style="width:100px;" />
</a>
Pipeline for BLAST-like search across
<a href="https://doi.org/10.1371/journal.pbio.3001421">all pre-2019 bacteria from ENA</a>
on standard desktop and laptops computers.
MOF-Search uses
<a href="https://brinda.eu/mof">
phylogenetically compressed assemblies and their <i>k</i>-mer
indexes</a>
to align batches of queries to them by
<a href="https://github.com/lh3/minimap2">Minimap 2</a>,
all within only several hours.
</p><br/>

<!-- vim-markdown-toc GFM -->

* [1. Introduction](#1-introduction)
  * [Citation](#citation)
* [2. Requirements](#2-requirements)
  * [a. Hardware](#a-hardware)
  * [b. Dependencies](#b-dependencies)
* [3. Installation](#3-installation)
  * [a. Step 1: Install dependencies](#a-step-1-install-dependencies)
  * [b. Step 2: Clone the repository](#b-step-2-clone-the-repository)
  * [c. Step 3: Run a simple test](#c-step-3-run-a-simple-test)
  * [d. Step 4: Download the database](#d-step-4-download-the-database)
* [4. Usage](#4-usage)
  * [a. Step 1: Copy or symlink your queries](#a-step-1-copy-or-symlink-your-queries)
  * [b. Step 2: Adjust configuration](#b-step-2-adjust-configuration)
  * [c. Step 3: Clean up intermediate files](#c-step-3-clean-up-intermediate-files)
  * [d. Step 4: Run the pipeline](#d-step-4-run-the-pipeline)
  * [e. Step 5: Analyze your results](#e-step-5-analyze-your-results)
* [5. Additional information](#5-additional-information)
  * [a. List of workflow commands](#a-list-of-workflow-commands)
  * [b. Directories](#b-directories)
  * [c. Running on a cluster](#c-running-on-a-cluster)
  * [d. Known limitations](#d-known-limitations)
* [6. License](#6-license)
* [7. Contacts](#7-contacts)

<!-- vim-markdown-toc -->


## 1. Introduction

The central idea behind MOF-Search,
enabling alignment locally at such a large scale,
is
[**phylogenetic compression**](https://brinda.eu/mof)
([paper](https://doi.org/10.1101/2023.04.15.536996)) -
a technique based
on using estimated evolutionary history to guide compression and
search of large genome collections using existing algorithms and
data structures.

In short, input data are reorganized according to the topology
of the estimated phylogenies, which makes data highly locally compressible even
using basic techniques. Existing software packages for compression, indexing,
and search - in this case [XZ](https://tukaani.org/xz/),
[COBS](https://github.com/iqbal-lab-org/cobs), and
[Minimap2](https://github.com/lh3/minimap2) - are then used as low-level tools.
The resulting performance gains come from a wide range of benefits of
phylogenetic compression, including easy parallelization, small memory
requirements, small database size, better memory locality, and better branch
prediction.

For more information about phylogenetic compression and the implementation details of MOF-Search, see the [corresponding
paper](https://www.biorxiv.org/content/10.1101/2023.04.15.536996v2) (including its
[supplementary material](https://www.biorxiv.org/content/biorxiv/early/2023/04/18/2023.04.15.536996/DC1/embed/media-1.pdf)
and visit the [associated website](https://brinda.eu/mof).


### Citation

> K. Břinda, L. Lima, S. Pignotti, N. Quinones-Olvera, K. Salikhov, R. Chikhi, G. Kucherov, Z. Iqbal, and M. Baym. **[Efficient and Robust Search of Microbial Genomes via Phylogenetic Compression.](https://doi.org/10.1101/2023.04.15.536996)** *bioRxiv* 2023.04.15.536996, 2023. https://doi.org/10.1101/2023.04.15.536996


## 2. Requirements

### a. Hardware

MOF-Search requires a standard desktop or laptop computer with an \*nix system,
and it can also run on a cluster. The minimal hardware requirements are **12 GB
RAM** and approximately **120 GB of disk space** (102 GB for the database and
a margin for intermediate files).


### b. Dependencies

MOF-Search is implemented as a [Snakemake](https://snakemake.github.io)
pipeline, using the Conda system to manage non-standard dependencies. Ensure you have [Conda](https://docs.conda.io/en/latest/miniconda.html) installed with the following packages:

* [GNU Time](https://www.gnu.org/software/time/) (on Linux present by default; on OS X, install with `brew install gnu-time`).
* [Python](https://www.python.org/) (>=3.7)
* [Snakemake](https://snakemake.github.io) (>=6.2.0)
* [Mamba](https://mamba.readthedocs.io/) (>= 0.20.0) - optional, but recommended

Additionally, MOF-Search uses standard Unix tools like
[GNU Make](https://www.gnu.org/software/make/),
[cURL](https://curl.se/),
[XZ Utils](https://tukaani.org/xz/), and
[GNU Gzip](https://www.gnu.org/software/gzip/).
These tools are typically included in standard \*nix installations. However, in minimal setups (e.g., virtualization, continuous integration), you might need to install them using the corresponding package managers.


## 3. Installation

### a. Step 1: Install dependencies

Make sure you have Conda and GNU Time installed. On Linux:
```bash
sudo apt-get install conda
```

On OS X (using Homebrew):
```bash
brew install conda
brew install gnu-time
```

Install Python (>=3.7), Snakemake (>=6.2.0), and Mamba (optional but recommended) using Conda:
```bash
conda install -y -c bioconda -c conda-forge \
    "python>=3.7" "snakemake>=6.2.0" "mamba>=0.20.0"
```


### b. Step 2: Clone the repository

Clone the MOF-Search repository from GitHub and navigate into the directory:

```bash
 git clone https://github.com/karel-brinda/mof-search
 cd mof-search
```


### c. Step 3: Run a simple test

Run the following command to ensure the pipeline works for sample queries and 3 batches (this will also install all additional dependencies using Conda):

```bash
make test
```

Make sure the test returns 0 (success) and that you see the expected output message:

```bash
 Success! Test run produced the expected output.
```


### d. Step 4: Download the database

Download all phylogenetically compressed assemblies and COBS *k*-mer
indexes for the [661k-HQ
collection](https://doi.org/10.1371/journal.pbio.3001421) by:
```bash
make download
```

The downloaded files will be located in the `asms/` and `cobs/` directories.


*Notes:*
* The compressed assemblies comprise *all* the genomes from the 661k
  collection.The COBS indexes comprise only those genomes that passed quality
  control.


## 4. Usage

### a. Step 1: Copy or symlink your queries

Remove the default test files or your old files in the `queries/` directory and
copy or symlink (recommended) your query files. The supported input formats are
FASTA and FASTQ, possibly gzipped. All query files will be preprocessed and
merged together.

*Notes:*
* All query names have to be unique among all query files.
* All non-`ACGT` characters in your query sequences will be translated to `A`.


### b. Step 2: Adjust configuration

Edit the [`config.yaml`](config.yaml) file for your desired search. All available options are
documented directly there.

### c. Step 3: Clean up intermediate files

Run `make clean` to clean intermediate files from the previous runs. This includes COBS matching files, alignment files, and various reports.

### d. Step 4: Run the pipeline

Simply run `make`, which will execute Snakemake with the corresponding parameters. If you want to run the pipeline step by step, run `make match` followed by `make map`.

### e. Step 5: Analyze your results

Check the output files in `output/`. The `.sam_summary.gz` files contain output alignments in a headerless SAM format. The `.sam_summary.stats` files contain statistics about your computed alignments.

If the results do not correspond to what you expected and you need to re-adjust
your search parameters, go to Step 2. If only the mapping part is affected by the
changes, you proceed more rapidly by manually removing the files in
`intermediate/05_map` and `output/` and running directly `make map`.


## 5. Additional information

### a. List of workflow commands

MOF-Search is executed via [GNU Make](https://www.gnu.org/software/make/), which handles all parameters and passes them to Snakemake.

Here's a list of all implemented commands (to be executed as `make {command}`):


```
######################
## General commands ##
######################
    all                  Run everything (the default rule)
    test                 Quick test using 3 batches
    help                 Print help messages
    clean                Clean intermediate search files
    cleanall             Clean all generated and downloaded files
####################
## Pipeline steps ##
####################
    conda                Create the conda environments
    download             Download the assemblies and COBS indexes
    match                Match queries using COBS (queries -> candidates)
    map                  Map candidates to assemblies (candidates -> alignments)
###############
## Reporting ##
###############
    viewconf             View configuration without comments
    report               Generate Snakemake report
##########
## Misc ##
##########
    cluster_slurm        Submit to a SLURM cluster
    cluster_lsf_test     Submit the test pipeline to LSF cluster
    cluster_lsf          Submit to LSF cluster
    format               Reformat Python and Snakemake files
```

### b. Directories

* `asms/`, `cobs/` Downloaded assemblies and COBS indexes
* `input/` Queries, to be provided within one or more FASTA/FASTQ files, possibly gzipped (`.fa`)
* `intermediate/` Intermediate files
   * `00_queries_preprocessed` Preprocessed queries
   * `01_queries_merged` Merged queries
   * `02_cobs_decompressed` Decompressed COBS indexes (temporary, used only in the disk mode is used)
   * `03_match` COBS matches
   * `04_filter` Filtered candidates
   * `05_map` Minimap2 alignments
* `logs/` Logs and benchmarks
* `output/` The resulting files (in a headerless SAM format)


### c. Running on a cluster

Running on a cluster is much faster as the jobs produced by this pipeline are quite light and usually start running as
soon as they are scheduled.

**For LSF clusters:**

1. Test if the pipeline is working on a LSF cluster: `make cluster_lsf_test`;
2. Configure you queries and run the full pipeline: `make cluster_lsf`;


### d. Known limitations

* **Swapping if the number of queries too high.** If the number of queries is
  too   high, the auxiliary Python scripts start to use too much memory, which
  may result in swapping. Try to keep the number of queries moderate and
  ideally their names short.

* **No support for ambiguous characters in queries.** As the tools used
  internally by MOF-Search support only the nucleotide alphabet, all non-ACGT
  characters in queries are first converted to A.


## 6. License

[MIT](https://github.com/karel-brinda/mof-search/blob/master/LICENSE)



## 7. Contacts

* [Karel Brinda](https://brinda.eu) \<karel.brinda@inria.fr\>
* [Leandro Lima](https://github.com/leoisl) \<leandro@ebi.ac.uk\>
