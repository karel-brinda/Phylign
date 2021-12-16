shell.prefix("set -euo pipefail")
from pathlib import Path

batches = [x.strip() for x in open("batches.txt")]
batches = [x for x in batches if x.find("gonorrhoeae") != -1]
print(batches)

cobs_url = f"http://ftp.ebi.ac.uk/pub/software/pandora/2020/cobs/karel"

asm_zenodo = 4602622
asms_url = f"https://zenodo.org/record/{asm_zenodo}/files"

qfiles = [x.with_suffix("").name for x in Path("queries").glob("*.fa")]
print(f"Query files: {qfiles}", file=sys.stderr)


rule all:
    input:
        [f"asms/{x}.tar.xz" for x in batches],
        [f"cobs/{x}.xz" for x in batches],
        [
            [
                f"intermediate/02_translated_matches/{batch}____{qfile}.xz"
                for batch in batches
            ]
            for qfile in qfiles
        ],


rule download_asm_batch:
    output:
        xz="asms/{batch}.tar.xz",
    params:
        url=asms_url,
    shell:
        """
        curl "{params.url}/{wildcards.batch}.tar.xz"  > {output.xz}
        """


rule download_cobs_batch:
    output:
        xz="cobs/{batch}.xz",
    params:
        url=cobs_url,
    shell:
        """
        curl "{params.url}/{wildcards.batch}.cobs_classic.xz"  > {output.xz}
        """


rule decompress_cobs:
    output:
        cobs="intermediate/00_cobs/{batch}.cobs",
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
    output:
        match="intermediate/01_match/{batch}____{qfile}.xz",
    input:
        cobs="intermediate/00_cobs/{batch}.cobs",
        fa="queries/{qfile}.fa",
    threads: 8
    # singularity:
    #     "docker://leandroishilima/cobs:1915fc"
    params:
        kmer_thres=0.5,
        cobs=cobs_linux,
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
    output:
        matches="intermediate/02_translated_matches/{batch}____{qfile}.xz",
    input:
        matches="intermediate/01_match/{batch}____{qfile}.xz",
    params:
        table="../leandro_name_translation/pseudonames_to_sample_names.tsv.xz",
    shell:
        """
        ./scripts/translate_cobs_matches.py {input.matches} {input.table} \
            | xz \
            > {output.matches}
        """
