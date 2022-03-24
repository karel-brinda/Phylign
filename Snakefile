shell.prefix("set -euo pipefail")
from pathlib import Path

# TODO:
# - limit parallel download threads
# - limit


batches = [x.strip() for x in open("batches.txt")]
# batches = [x for x in batches if x.find("gonorrhoeae") != -1]
print(batches)

cobs_url = f"http://ftp.ebi.ac.uk/pub/software/pandora/2020/cobs/karel"


def cobs_url(wildcards):
    x = wildcards.batch
    if x >= "eubacterium":
        return f"https://zenodo.org/record/6345389/files/{x}.cobs_classic.xz"
    else:
        return f"https://zenodo.org/record/6347571/files/{x}.cobs_classic.xz"


asm_zenodo = 4602622
asms_url = f"https://zenodo.org/record/{asm_zenodo}/files"

qfiles = [x.with_suffix("").name for x in Path("queries").glob("*.fa")]
print(f"Query files: {qfiles}")

##########################################################################


wildcard_constraints:
    batch=".+__\d\d",


rule all:
    input:
        #[f"intermediate/02_filter/{qfile}.fa" for qfile in qfiles],
        #
        #"intermediate/03_map/{batch}__{qfile}.sam
        [f"output/{qfile}.sam_summary.xz" for qfile in qfiles],
        #[
        #    [f"intermediate/03_map/{batch}____{qfile}.sam" for batch in batches]
        #    for qfile in qfiles
        #],


#        [
#            [f"intermediate/02_translate/{batch}____{qfile}.xz" for batch in batches]
#            for qfile in qfiles
#        ],


rule download:
    input:
        [f"asms/{x}.tar.xz" for x in batches],
        [f"cobs/{x}.xz" for x in batches],



rule download_asm_batch:
    """Download compressed assemblies
    """
    output:
        xz="asms/{batch}.tar.xz",
    params:
        url=asms_url,
    resources:
        download_thr=1
    shell:
        """
        curl "{params.url}/{wildcards.batch}.tar.xz"  > {output.xz}
        set +o pipefail && xzcat {output.xz} | head -c 20
        """


rule download_cobs_batch:
    """Download compressed cobs indexes
    """
    output:
        xz="cobs/{batch}.xz",
    params:
        url=cobs_url,
    resources:
        download_thr=1
    shell:
        """
        curl "{params.url}"  > {output.xz}
        set +o pipefail && xzcat {output.xz} | head -c 20
        """


rule decompress_cobs:
    """Decompress cobs indexes
    """
    output:
        cobs=temp("intermediate/00_cobs/{batch}.cobs"),
    input:
        xz="cobs/{batch}.xz",
    resources:
        decomp_thr=1
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
        match=protected("intermediate/01_match/{batch}____{qfile}.xz"),
    input:
        cobs="intermediate/00_cobs/{batch}.cobs",
        fa="queries/{qfile}.fa",
    threads: workflow.cores - 1
    # singularity:
    #     "docker://leandroishilima/cobs:1915fc"
    params:
        kmer_thres=0.33,
        cobs=cobs_linux,
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


# ./scripts/filter_queries.py -q ./queries/gc01_1kl.fa ./intermediate/01_match/*.xz  |L


rule translate_matches:
    """Translate cobs matches.

    Output:
        ref - read - matches
    """
    output:
        fa="intermediate/02_filter/{qfile}.fa",
    input:
        fa="queries/{qfile}.fa",
        all_matches=[
            f"intermediate/01_match/{batch}____{{qfile}}.xz" for batch in batches
        ],
    shell:
        """
        ./scripts/filter_queries.py -q {input.fa} {input.all_matches} \
            > {output.fa}
        """


rule minimap2:
    output:
        sam="intermediate/03_map/{batch}____{qfile}.sam",
    input:
        qfa="intermediate/02_filter/{qfile}.fa",
        asm="asms/{batch}.tar.xz",
    shell:
        """
        ./scripts/batch_align.py \\
            {input.asm} \\
            {input.qfa} \\
            > {output.sam}
        """


rule aggregate_sams:
    output:
        pseudosam="output/{qfile}.sam_summary.xz",
    input:
        sam=[f"intermediate/03_map/{batch}____{{qfile}}.sam" for batch in batches],
    shell:
        """
        head -n 9999999 {input.sam} \
            | grep -v "@" \
            | xz \
            > {output.pseudosam}
        """


# rule translate_matches:
#    """Translate cobs matches.
#
#    Output:
#        ref - read - matches
#    """
#    output:
#        matches="intermediate/02_translate/{batch}____{qfile}.xz",
#    input:
#        matches="intermediate/01_match/{batch}____{qfile}.xz",
#    shell:
#        """
#        ./scripts/translate_cobs_matches.py {input.matches} \
#            | xz \
#            > {output.matches}
#        """
