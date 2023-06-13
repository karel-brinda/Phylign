# MOF-Search

MOF-Search is a pipeline for BLAST-like search across all pre-2019 bacteria from ENA (the [661k collection](https://doi.org/10.1371/journal.pbio.3001421)).

<!-- vim-markdown-toc GFM -->

* [Dependencies](#dependencies)
  * [Non-standard](#non-standard)
  * [Standard](#standard)
  * [Benchmarking](#benchmarking)
* [Walkthrough](#walkthrough)
* [Commands](#commands)
* [Running on a cluster](#running-on-a-cluster)
  * [Running on a LSF cluster](#running-on-a-lsf-cluster)
* [Directories](#directories)
* [Notes](#notes)
  * [Non-`ACGT` bases](#non-acgt-bases)
  * [Query files](#query-files)
  * [Query names](#query-names)
* [Contacts](#contacts)

<!-- vim-markdown-toc -->


## Dependencies

Some dependencies are packaged into `conda` environments that `snakemake` will automatically create.
Others are non-standard (which you might need to install) and standard (which you probably have).


### Non-standard
* `python >= 3.7`
* `snakemake >= 6.2.0`
* `mamba >= 0.20.0`

### Standard
* `bash`
* `make`
* `curl`
* `xz`
* `head`
* `grep`
* `awk`
* `diff`
* `cat`
* `gzip`
* `cut`

### Benchmarking

If you want to benchmark the pipeline and is on `Mac OS X`, you need to install `gnu-time`:
```
brew install gnu-time
```

You will also get more benchmarking stats if `psutil` is installed.

## Walkthrough

This is our recommended steps to run `mof-search`:

1. Run `make test` to ensure the pipeline works for the sample queries and just 3 batches. This will also setup `COBS`;
    * Note: `make test` should return 0 (success) and you should have the following message at the end of the execution,
    to ensure the test produced the expected output:
    ```
    Files output/backbone19Kbp___ecoli_reads_1___ecoli_reads_2___gc01_1kl.sam_summary.xz and data/backbone19Kbp___ecoli_reads_1___ecoli_reads_2___gc01_1kl.sam_summary.xz are identical
    ```
    If the test did not produce the expected output, you should get this error message:
    ```
    Files output/backbone19Kbp___ecoli_reads_1___ecoli_reads_2___gc01_1kl.sam_summary.xz and data/backbone19Kbp.fa differ
    make: *** [Makefile:21: test] Error 1
    ```
2. Run `make download` to download all the assemblies and batches for the 661k;
3. Run `make clean` to clean the intermediate files from the previous run;
4. Add your desired queries to the `queries` directory and remove the sample ones;
5. Run `make` to run align your queries to the 661k.



## Commands

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

## Running on a cluster

Running on a cluster is much faster as the jobs produced by this pipeline are quite light and usually start running as
soon as they are scheduled.

### Running on a LSF cluster

1. Test if the pipeline is working on a LSF cluster: `make cluster_lsf_test`;
2. Configure you queries and run the full pipeline: `make cluster_lsf`;

## Directories

* `asms/`, `cobs/` Downloaded assemblies and COBS indexes
* `queries/` Queries, to be provided within one or more FASTA files (`.fa`)
* `intermediate/` Intermediate files
   * `00_cobs` Decompressed COBS indexes (tmp)
   * `01_match` COBS matches
   * `02_filter` Filtered candidates
   * `03_map` Minimap2 alignments
   * `fixed_queries` Sanitized queries
* `output/` Results



## Notes

### Non-`ACGT` bases

All non-`ACGT` bases in your queries are transformed into `A`.

### Query files

Try to keep the number of query files low or their name short.
If you have tens or hundreds or more query files, concatenate them all into one before running `mof-search`.

### Query names

For now, all query names have to be unique among all query files.



## Contacts

[Karel Brinda](http://karel-brinda.github.io) \<karel.brinda@inria.fr\>

[Leandro Lima](https://github.com/leoisl) \<leandro@ebi.ac.uk\>
