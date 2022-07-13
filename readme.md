# MOF-search

This is the pipeline for BLAST-like search within the 661k collection.


## Dependencies

* `snakemake`
* `cobs`
* `minimap2`
* `curl`
* `pprint`
* `xz`
* `yq`
* `xopen`



## Commands

* `make`          Run everything
* `make download` Download the 661k assemblies and COBS indexes
* `make match`    Match queries using COBS (queries -> candidates)
* `make map`      Map candidates to the assemblies (candidates -> alignments)
* `make report`   Generate Snakemake report
* `make clean`    Clean intermediate search files
* `make cleanall` Clean all generated and downloaded file



## Directories

* `asms/`, `cobs/` Downloaded assemblies and COBS indexes
* `queries/` Queries, to be provided within one or more FASTA files (`.fa`) in the 1line format (!!)
* `intermediate/` Intermediate files
   * `00_cobs` Decompressed COBS indexes (tmp)
   * `01_match` COBS matches
   * `02_filter` Filtered candidates
   * `03_map` Minimap2 alignments
* `output/` Results
