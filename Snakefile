shell.prefix("set -euo pipefail")
from pathlib import Path

batches = [x.strip() for x in open("batches.txt")]
batches = [x for x in batches if x.find("gonorrhoeae") != -1]
print(batches)

cobs_url = f"http://ftp.ebi.ac.uk/pub/software/pandora/2020/cobs/karel"

def cobs_url(wildcards):
    x=wildcards.batch
    if x>"escherichia_coli_":
        return f"https://zenodo.org/record/6345389/files/{x}.cobs_classic.xz"
    else:
        return f"https://zenodo.org/record/6347571/files/{x}.cobs_classic.xz"


asm_zenodo = 4602622
asms_url = f"https://zenodo.org/record/{asm_zenodo}/files"

qfiles = [x.with_suffix("").name for x in Path("queries").glob("*.fa")]
print(f"Query files: {qfiles}", file=sys.stderr)


rule all:
    input:
        [f"asms/{x}.tar.xz" for x in batches],
        [f"cobs/{x}.xz" for x in batches],
        [
            [f"intermediate/02_translate/{batch}____{qfile}.xz" for batch in batches]
            for qfile in qfiles
        ],


rule download_asm_batch:
    """Download compressed assemblies
    """
    output:
        xz="asms/{batch}.tar.xz",
    params:
        url=asms_url,
    shell:
        """
        curl "{params.url}/{wildcards.batch}.tar.xz"  > {output.xz}
        """


rule download_cobs_batch:
    """Download compressed cobs indexes
    """
    output:
        xz="cobs/{batch}.xz",
    params:
        url=cobs_url
    shell:
        """
        curl "{params.url}"  > {output.xz}
        """


rule decompress_cobs:
    """Decompress cobs indexes
    """
    output:
        cobs=temp("intermediate/00_cobs/{batch}.cobs"),
    input:
        xz="cobs/{batch}.xz",
    shell:
        """
        xzcat "{input.xz}" > "{output.cobs}"
        """


cobs_mac = """docker run \\
    -v $PWD:/experiment \\
    --workdir /experiment \\
    leandroishilima/cobs:1915fc query \\
"""
cobs_linux = ("cobs query --load-complete",)


rule run_cobs:
    """Cobs matching
    """
    output:
        match="intermediate/01_match/{batch}____{qfile}.xz",
    input:
        cobs="intermediate/00_cobs/{batch}.cobs",
        fa="queries/{qfile}.fa",
    threads: workflow.cores - 1
    # singularity:
    #     "docker://leandroishilima/cobs:1915fc"
    params:
        kmer_thres=0.33,
        cobs=cobs_mac,
    priority: 999
    shell:
        """
        {params.cobs} \\
            -t {params.kmer_thres} \\
            -T {threads} \\
            -i {input.cobs} \\
            -f {input.fa} \\
            | xz -v \\
            > {output.match}
            ##--load-complete \\
        """


rule translate_matches:
    """Translate cobs matches.

    Output:
        ref - read - matches
    """
    output:
        matches="intermediate/02_translate/{batch}____{qfile}.xz",
    input:
        matches="intermediate/01_match/{batch}____{qfile}.xz",
    shell:
        """
        ./scripts/translate_cobs_matches.py {input.matches} \
            | xz \
            > {output.matches}
        """

rule merge_and_filter:
    """
    """
