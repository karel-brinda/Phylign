from pathlib import Path
import subprocess


def count_kmers(batch_dir: Path, reads_file: Path, kmer_size: int, kmer_counts_filename: Path):
    with open(kmer_counts_filename, "w") as kmer_counts_fh:
        for file in batch_dir.iterdir():
            if file.name.endswith(".fa.gz"):
                file = file.resolve()
                subprocess.check_call(f"zcat {file} | jellyfish count --canonical -m {kmer_size} -s 100M -t 1 --if {reads_file} /dev/fd/0", shell=True)
                kmer_counts = subprocess.check_output(f"jellyfish dump mer_counts.jf", shell=True)
                kmer_counts = kmer_counts.decode("utf-8")
                kmer_counts = kmer_counts.strip().split("\n")

                kmer_present = 0
                kmer_absent = 0
                for line in kmer_counts:
                    if line[0] == ">":
                        line = line.strip()
                        if line != ">0":
                            kmer_present += 1
                        else:
                            kmer_absent += 1
                sample = file.name.split(".")[0]
                print(
                    f"{sample} {kmer_present} {kmer_absent} {kmer_present / (kmer_present + kmer_absent)}",
                    file=kmer_counts_fh)


count_kmers(Path(snakemake.input.assembly_batch),
            Path(snakemake.input.reads),
            int(snakemake.params.k),
            Path(snakemake.output.kmer_counts))
