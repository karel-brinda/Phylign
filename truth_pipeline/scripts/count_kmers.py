from pathlib import Path
import subprocess


def count_kmers(batch_dir: Path, reads_file: Path, kmer_size: int, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    for file in batch_dir.iterdir():
        if file.name.endswith(".fa.gz"):
            file = file.resolve()
            filename = file.name
            kmer_counts_file = output_dir/f"{filename}.kmer_counting.k_{kmer_size}.fa"
            subprocess.check_call(f"zcat {file} | jellyfish count --canonical -m {kmer_size} -s 100M -t 1 --if {reads_file} /dev/fd/0", shell=True)
            subprocess.check_call(f"jellyfish dump mer_counts.jf > {kmer_counts_file}", shell=True)


count_kmers(Path(snakemake.input.assembly_batch),
            Path(snakemake.input.reads),
            int(snakemake.params.k),
            Path(snakemake.output.kmer_dir))
