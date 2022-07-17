# MOF-search

This is the pipeline for BLAST-like search within the 661k collection.


## Dependencies

:warning: **`Mac OS X` users have to necessarily install `gcc-11` to run `mof-search`. The easiest way is through `brew`:**
```
brew install gcc@11
```



Some dependencies are packaged into `conda` environments that `snakemake` will automatically create.
Others are non-standard (which you might need to install) and stardard (which you probably have).


### Non-standard
* `python3`
* `snakemake`
* `mamba`

### Standard
* `bash`
* `make`
* `curl`
* `xz`
* `sed`
* `head`
* `grep`
* `awk`

## Walkthrough

This is our recommended steps to run `mof-search`:

1. Run `make test` to ensure the pipeline works for the sample queries and just 3 batches. This will also setup `COBS`;
2. Run `make download` to download all the assemblies and batches for the 661k;
3. Run `make clean` to clean the intermediate files from the previous run;
4. Add your desired queries to the `queries` directory and remove the sample ones;
5. Run `make` to run align your queries to the 661k.

## Commands

* `make`          Run everything
* `make test`     Run the queries on 3 batches, to test the pipeline completely
* `make download` Download the 661k assemblies and COBS indexes
* `make match`    Match queries using COBS (queries -> candidates)
* `make map`      Map candidates to the assemblies (candidates -> alignments)
* `make report`   Generate Snakemake report
* `make clean`    Clean intermediate search files
* `make cleanall` Clean all generated and downloaded file



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
