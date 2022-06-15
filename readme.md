# MOF-search

This is the pipeline for BLAST-like search within the 661k collection.


## Commands

* `make` Run everything
* `make download` Download the 661k assemblies and COBS indexes
* `make match`    Match queries using COBS (queries -> candidates)
* `make map`      Map candidates to the assemblies (candidates -> alignments)
* `make report`   Generate Snakemake report
* `make clean`    Clean intermediate search files
* `make cleanall` Clean all generated and downloaded file
