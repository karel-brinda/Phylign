# MOF-search

This is the pipeline for BLAST-like search within the 661k collection.

## Commands

* `make all` Run everything
* `download` Download the 661k assemblies and COBS indexes
* `match`    Match queries using COBS (queries -> candidates)
* `map`      Map candidates to the assemblies (candidates -> alignments)
* `report`   Generate Snakemake report
* `clean`    Clean intermediate search files
* `cleanall` Clean all generated and downloaded file
