batches = [x.strip() for x in open("batches.txt")]
batches = [x for x in batches if x.find("gonorrhoeae") != -1]
print(batches)

cobs_url = (
    f"http://ftp.ebi.ac.uk/pub/software/pandora/2020/cobs/karel/compressed_indexes"
)

asm_zenodo = 4602622
asms_url = f"https://zenodo.org/record/{asm_zenodo}/files"


rule all:
    input:
        [f"asms/{x}.tar.xz" for x in batches],
        [f"cobs/{x}.xz" for x in batches],


rule download_asm_batch:
    output:
        xz="asms/{name}.xz",
    params:
        url=asms_url,
    shell:
        """
        curl "{params.url}/{wildcards.name}.tar.xz"  > {output.xz}
        """


rule download_cobs_batch:
    output:
        xz="cobs/{name}.xz",
    params:
        url=cobs_url,
    shell:
        """
        curl "{params.url}/{wildcards.name}.cobs_classic.xz"  > {output.xz}
        """
