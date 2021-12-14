batches = [x.strip() for x in open("batches.txt")]
print(batches)

burl = f"http://ftp.ebi.ac.uk/pub/software/pandora/2020/cobs/karel/compressed_indexes/"


rule all:
    input:
        "final_cobs_file_stats.tsv"

rule merge_stats:
    output:
        "final_cobs_file_stats.tsv"
    input:
        [f"{x}.cobs_classic.xz.size" for x in batches],
    shell:
        """
           cat {input} \\
               | awk 'x[$1]++==0' \\
               > {output}
        """


rule size:
    output:
        txt="{name}.cobs_classic.xz.size",
    input:
        xz="{name}.cobs_classic.xz",
    shell:
        """
        a=$(cat {input.xz} | wc -c)
        b=$(xzcat {input.xz} | wc -c)
        (
            printf "%s\t%s\t%s\n" batch cobs_bytes cobs_xz_bytes
            printf "%s\t%s\t%s\n" {wildcards.name} $b $a
        ) > {output.txt}
        """


rule download:
    output:
        xz="{name}.cobs_classic.xz",
    params:
        burl=burl,
    shell:
        """
        curl "{params.burl}/{wildcards.name}.cobs_classic.xz"  > {output.xz}
        """
