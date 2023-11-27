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

* [Introduction](#introduction)
  * [Citation](#citation)
* [Dependencies](#dependencies)
* [Installation](#installation)
  * [Step 1: Install dependencies](#step-1-install-dependencies)
  * [Step 2: Clone the repository](#step-2-clone-the-repository)
  * [Step 3: Run a simple test](#step-3-run-a-simple-test)
  * [Step 4: Download the database](#step-4-download-the-database)
* [Usage](#usage)
  * [Step 1: Copy or symlink your queries](#step-1-copy-or-symlink-your-queries)
  * [Step 2: Adjust configuration](#step-2-adjust-configuration)
  * [Step 3: Clean up intermediate files](#step-3-clean-up-intermediate-files)
  * [Step 4: Run the pipeline](#step-4-run-the-pipeline)
  * [Step 5: Analyze your results](#step-5-analyze-your-results)
* [Additional information](#additional-information)
  * [List of workflow commands](#list-of-workflow-commands)
  * [Directories](#directories)
  * [Running on a cluster](#running-on-a-cluster)
  * [Known limitations](#known-limitations)
* [License](#license)
* [Contacts](#contacts)

<!-- vim-markdown-toc -->


## Introduction

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

For more information about phylogenetic compression and implementation details
of MOF-Search, see the [corresponding
paper](https://www.biorxiv.org/content/10.1101/2023.04.15.536996v2) (and its
[supplementary](https://www.biorxiv.org/content/biorxiv/early/2023/04/18/2023.04.15.536996/DC1/embed/media-1.pdf)
and the associated website [phylogenetic compression and MOF](https://brinda.eu/mof).


### Citation

> K. Břinda, L. Lima, S. Pignotti, N. Quinones-Olvera, K. Salikhov, R. Chikhi, G. Kucherov, Z. Iqbal, and M. Baym. **[Efficient and Robust Search of Microbial Genomes via Phylogenetic Compression.](https://doi.org/10.1101/2023.04.15.536996)** *bioRxiv* 2023.04.15.536996, 2023. https://doi.org/10.1101/2023.04.15.536996


## Dependencies

MOF-Search requires a standard desktop or laptop computer with an \*nix system, and can be run also on a
cluster. The minimal hardware requirements are *12 GB RAM* and approximately *120 GB of disk space* (102 GB
for the database and a margin for the intermediate files).


## Installation

### Step 1: Install dependencies

MOF-Search is implemented as a [Snakemake](https://snakemake.github.io)
pipeline, using the Conda system to manage all non-standard dependencies. To function smoothly, we recommend having Conda with the following packages:


* [Conda](https://docs.conda.io/en/latest/miniconda.html)
* [GNU Time](https://www.gnu.org/software/time/) (on Linux present by default, on OS X can be installed by
  `brew install gnu-time`).
* [Python](https://www.python.org/) (>=3.7)
* [Snakemake](https://snakemake.github.io) (>=6.2.0)
* [Mamba](https://mamba.readthedocs.io/) (>= 0.20.0) - optional, recommended

The last three packages can be installed using Conda by
```bash
    conda install -y -c bioconda -c conda-forge \
        "python>=3.7" "snakemake>=6.2.0" "mamba>=0.20.0"
```

Besides that, MOF-Search uses a multitude of standard Unix tools, such as
[GNU Make](https://www.gnu.org/software/make/),
[cURL](https://curl.se/),
[XZ Utils](https://tukaani.org/xz/), and
[GNU Gzip](https://www.gnu.org/software/gzip/). These tools are usually present in standard \*nix installations, but they might be missing in minimal image setups, such as those used for virtualization, contiguous integration, etc. In such as case, install the missing tools by the corresponding package managers.:w



### Step 2: Clone the repository

```bash
   git clone https://github.com/karel-brinda/mof-search
   cd mof-search
```

### Step 3: Run a simple test

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


### Step 4: Download the database

Run `make download` to download from Zenodo all the remaining phylogenetically
compressed assemblies and COBS *k*-mer indexes for the [661k-HQ
collection](https://doi.org/10.1371/journal.pbio.3001421). The downloaded files
will then be located in the `asms/` and `cobs/` directories.

*Notes:*
* The compressed assemblies comprise *all* the genomes from the 661k
  collection.The COBS indexes comprise only those genomes that passed quality
  control.
* For file accessions, see the [MOF
  website](http://karel-brinda.githbub.io/mof).


## Usage

### Step 1: Copy or symlink your queries

Remove the default test files or you old files in the `queries/` directory and
copy or symlink (recommended) your query files. The supported input formats are
FASTA and FASTQ, possibly gzipped. All query files will be preprocessed and
merged together.

*Notes:*
* All query names have to be unique among all query files.
* All non-`ACGT` characters in your query sequences will be translated to `A`.


### Step 2: Adjust configuration

Edit the [`config.yaml`](config.yaml) file for your desired search. All available options are
documented directly there.

### Step 3: Clean up intermediate files

Run `make clean` to clean the intermediate files from the previous runs. This includes COBS matching files, alignment files, and various reports.

### Step 4: Run the pipeline

Simply run `make`, which will execute Snakemake with the corresponding parameters. If you want to run the pipeline step by step, run `make match` followed by `make map`.

### Step 5: Analyze your results

Check the output files in `results/`.

If the results don't correspond to what you expected and you need to re-adjust your parameters, go to Step 2. If only the mapping part is affected by the changes, you proceed more rapidly, by manually removing the files in `intermediate/03_map` and `output/` and running directly `make map`.


## Additional information

### List of workflow commands

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


### Running on a cluster

Running on a cluster is much faster as the jobs produced by this pipeline are quite light and usually start running as
soon as they are scheduled.

**For LSF clusters:**

1. Test if the pipeline is working on a LSF cluster: `make cluster_lsf_test`;
2. Configure you queries and run the full pipeline: `make cluster_lsf`;


### Known limitations


* When the number of queries is too high, the auxiliary Python scripts start to
  use too much memory, which may result in swapping. Try to keep the number of
  queries moderate and ideally their names short. If you have tens or hundreds
  or more query files, concatenate them all into one before running
  `mof-search`.


## License

[MIT](https://github.com/karel-brinda/mof-search/blob/master/LICENSE)



## Contacts

* [Karel Brinda](https://brinda.eu) \<karel.brinda@inria.fr\>
* [Leandro Lima](https://github.com/leoisl) \<leandro@ebi.ac.uk\>
