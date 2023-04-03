import glob
from pathlib import Path
from snakemake.utils import min_version
import re

##################################
## Helper functions
##################################


extensions = ["fa", "fasta", "fq", "fastq"]


def multiglob(patterns):
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    files = list(map(Path, files))
    return files


def get_all_query_filepaths():
    return multiglob(expand("queries/*.{ext}", ext=extensions))


def get_all_query_filenames():
    return sorted([file.with_suffix("").name for file in get_all_query_filepaths()])


def get_batches():
    with open(config["batches"]) as fin:
        return sorted([x.strip() for x in fin])


def get_filename_for_all_queries():
    return "___".join(get_all_query_filenames())


def get_index_metadata(wildcards, input):
    batch = wildcards.batch
    decompressed_indexes_sizes_filepath = input.decompressed_indexes_sizes
    with open(decompressed_indexes_sizes_filepath) as decompressed_indexes_sizes_fh:
        for line in decompressed_indexes_sizes_fh:
            cobs_index, size_in_bytes, xz_decompress_RAM = line.strip().split()
            batch_for_cobs_index = cobs_index.split("/")[-1].replace(
                ".cobs_classic.xz", ""
            )
            size_in_bytes = int(size_in_bytes)
            xz_decompress_RAM = int(xz_decompress_RAM)
            if batch == batch_for_cobs_index:
                return size_in_bytes, xz_decompress_RAM

    assert (
        False
    ), f"Error getting uncompressed batch size for batch {batch}: batch not found"


def get_uncompressed_batch_size(wildcards, input):
    return get_index_metadata(wildcards, input)[0]


def get_xz_decompress_RAM(wildcards, input):
    return get_index_metadata(wildcards, input)[1]


def get_uncompressed_batch_size_in_MB(wildcards, input, ignore_RAM, streaming):
    if ignore_RAM:
        return 0
    if streaming:
        # then we are decompressing and running cobs at the same time
        xz_decompression_RAM_usage_in_bytes = get_xz_decompress_RAM(wildcards, input)
        xz_decompression_RAM_usage_in_MB = (
            int(xz_decompression_RAM_usage_in_bytes / 1024 / 1024) + 1
        )
    else:
        xz_decompression_RAM_usage_in_MB = 0
    size_in_bytes = get_uncompressed_batch_size(wildcards, input)
    size_in_MB = int(size_in_bytes / 1024 / 1024) + 1
    return size_in_MB + xz_decompression_RAM_usage_in_MB


def get_max_number_of_COBS_threads_from_auto_string(auto_string):
    cobs_threads = re.findall(r"auto\((\d+)\)", auto_string)
    parsing_was_successful = len(cobs_threads) == 1
    assert parsing_was_successful, "Error parsing parameter cobs_threads parameter"
    cobs_threads = int(cobs_threads[0])
    return cobs_threads


def get_number_of_COBS_threads(wildcards, input, predefined_cobs_threads, streaming):
    user_defined_nb_of_threads = not predefined_cobs_threads.startswith("auto")
    if user_defined_nb_of_threads:
        return int(predefined_cobs_threads)

    use_max_cores = predefined_cobs_threads == "auto"
    if use_max_cores:
        max_number_of_COBS_threads = workflow.cores
    else:
        max_number_of_COBS_threads = get_max_number_of_COBS_threads_from_auto_string(
            predefined_cobs_threads
        )

    uncompressed_batch_size_in_MB = get_uncompressed_batch_size_in_MB(
        wildcards, input, ignore_RAM=False, streaming=streaming
    )
    max_RAM_MB = int(config["max_ram_gb"]) * 1024
    number_of_cores_to_use = round(
        uncompressed_batch_size_in_MB / max_RAM_MB * max_number_of_COBS_threads
    )
    number_of_cores_to_use = max(number_of_cores_to_use, 1)
    number_of_cores_to_use = min(number_of_cores_to_use, max_number_of_COBS_threads)
    is_using_more_than_half_of_the_cores = (
        number_of_cores_to_use > max_number_of_COBS_threads / 2
    )
    if is_using_more_than_half_of_the_cores:
        # usually in this situation we run just one COBS jobs simultaneously. Better then to use all cores then
        number_of_cores_to_use = max_number_of_COBS_threads
    return number_of_cores_to_use


def get_index_load_mode():
    allowed_index_load_modes = ["mem-stream", "mem-disk", "mmap-disk"]
    index_load_mode = config["index_load_mode"]
    assert (
        index_load_mode in allowed_index_load_modes
    ), f"index_load_mode must be one of {allowed_index_load_modes}"
    return index_load_mode


##################################
## Initialization
##################################


configfile: "config.yaml"


min_version("6.2.0")
shell.prefix("set -euo pipefail")

batches = get_batches()
print(f"Batches: {batches}")

qfiles = get_all_query_filepaths()
print(f"Query files: {list(map(str, qfiles))}")

assemblies_dir = Path(f"{config['download_dir']}/asms")
cobs_dir = Path(f"{config['download_dir']}/cobs")
decompression_dir = Path(config.get("decompression_dir", "intermediate/00_cobs"))
keep_cobs_indexes = config["keep_cobs_indexes"]
predefined_cobs_threads = str(config["cobs_threads"])
ignore_RAM = False
load_complete = False
streaming = False
cobs_is_an_IO_heavy_job = False
index_load_mode = get_index_load_mode()

if index_load_mode == "mem-stream":
    # this parameter is ignored because we never decompress indexes to disk with this load mode
    keep_cobs_indexes = False
    load_complete = True
    streaming = True
elif index_load_mode == "mem-disk":
    load_complete = True
elif index_load_mode == "mmap-disk":
    # we ignore RAM usage because the OS is responsible for controlling RAM usage in this case
    ignore_RAM = True
    # we set cobs as an IO-heavy job because during its execution it might access the disk several times
    # due to mmap
    cobs_is_an_IO_heavy_job = True


wildcard_constraints:
    batch=".+__\d\d",


if keep_cobs_indexes:

    ruleorder: decompress_cobs > run_cobs > decompress_and_run_cobs


else:

    ruleorder: decompress_and_run_cobs > decompress_cobs > run_cobs


##################################
## Download params
##################################


def cobs_url_fct(wildcards):
    x = wildcards.batch
    if x >= "eubacterium":
        return f"https://zenodo.org/record/6849657/files/{x}.cobs_classic.xz"
    else:
        return f"https://zenodo.org/record/6845083/files/{x}.cobs_classic.xz"


asm_zenodo = 4602622
asms_url = f"https://zenodo.org/record/{asm_zenodo}/files"


##################################
## Top-level rules
##################################


rule all:
    """Run all
    """
    input:
        f"output/{get_filename_for_all_queries()}.sam_summary.gz",
        f"output/{get_filename_for_all_queries()}.sam_summary.stats",


rule download:
    """Download assemblies and COBS indexes.
    """
    input:
        [f"{assemblies_dir}/{x}.tar.xz" for x in batches],
        [f"{cobs_dir}/{x}.cobs_classic.xz" for x in batches],


rule match:
    """Match reads to the COBS indexes.
    """
    input:
        f"intermediate/02_filter/{get_filename_for_all_queries()}.fa",


rule map:
    """Map reads to the assemblies.
    """
    input:
        f"output/{get_filename_for_all_queries()}.sam_summary.gz",
        f"output/{get_filename_for_all_queries()}.sam_summary.stats",


##################################
## Download rules
##################################
rule download_asm_batch:
    """Download compressed assemblies
    """
    output:
        xz=f"{assemblies_dir}/{{batch}}.tar.xz",
    params:
        url=asms_url,
    resources:
        max_download_threads=1,
    threads: 1
    shell:
        """
        curl "{params.url}/{wildcards.batch}.tar.xz"  > {output.xz}
        scripts/test_xz.py {output.xz}
        """


rule download_cobs_batch:
    """Download compressed cobs indexes
    """
    output:
        xz=f"{cobs_dir}/{{batch}}.cobs_classic.xz",
    params:
        url=cobs_url_fct,
    resources:
        max_download_threads=1,
    threads: 1
    shell:
        """
        curl "{params.url}"  > {output.xz}
        scripts/test_xz.py {output.xz}
        """


##################################
## Processing rules
##################################
def get_query_file(wildcards):
    query_file = multiglob(expand(f"queries/{wildcards.qfile}.{{ext}}", ext=extensions))
    assert len(query_file) == 1
    return query_file[0]


rule fix_query:
    """Fix query to expected COBS format: single line fastas composed of ACGT bases only
    """
    output:
        fixed_query="intermediate/fixed_queries/{qfile}.fa",
    input:
        original_query=get_query_file,
    threads: 1
    conda:
        "envs/seqtk.yaml"
    params:
        base_to_replace="A",
    shell:
        """
        seqtk seq -A -U -C {input.original_query} \\
                | awk '{{if(NR%2==1){{print $0;}}else{{gsub(/[^ACGT]/, \"{params.base_to_replace}\"); print;}}}}' \\
            > {output.fixed_query}
        """


rule concatenate_queries:
    """Concatenate all queries into a single file, so we just need to run COBS/minimap2 just once per batch
    """
    output:
        concatenated_query=f"intermediate/concatenated_query/{get_filename_for_all_queries()}.fa",
    input:
        all_queries=expand(
            "intermediate/fixed_queries/{qfile}.fa", qfile=get_all_query_filenames()
        ),
    threads: 1
    shell:
        """
        cat {input} > {output}
        """


rule decompress_cobs:
    """Decompress cobs indexes
    """
    output:
        cobs_index=f"{decompression_dir}/{{batch}}.cobs_classic",
    input:
        xz=f"{cobs_dir}/{{batch}}.cobs_classic.xz",
    resources:
        max_io_heavy_threads=1,
    params:
        cobs_index_tmp=f"{decompression_dir}/{{batch}}.cobs_classic.tmp",
    # The same number as of COBS threads to ensure that COBS is executed immediately after decompression
    threads: lambda wildcards, input: get_number_of_COBS_threads(
    wildcards, input, predefined_cobs_threads, streaming
)
    shell:
        """
        ./scripts/benchmark.py --log logs/benchmarks/decompress_cobs/{wildcards.batch}.txt \\
            'xzcat --no-sparse --ignore-check "{input.xz}" > "{params.cobs_index_tmp}" \\
            && mv "{params.cobs_index_tmp}" "{output.cobs_index}"'
        """


rule run_cobs:
    """Cobs matching
    """
    output:
        match="intermediate/01_match/{batch}____{qfile}.gz",
    input:
        cobs_index=f"{decompression_dir}/{{batch}}.cobs_classic",
        fa="intermediate/concatenated_query/{qfile}.fa",
        decompressed_indexes_sizes="data/decompressed_indexes_sizes.txt",
    resources:
        max_io_heavy_threads=int(cobs_is_an_IO_heavy_job),
        max_ram_mb=lambda wildcards, input: get_uncompressed_batch_size_in_MB(
            wildcards, input, ignore_RAM, streaming
        ),
    threads: lambda wildcards, input: get_number_of_COBS_threads(
    wildcards, input, predefined_cobs_threads, streaming
)
    params:
        kmer_thres=config["cobs_kmer_thres"],
        load_complete="--load-complete" if load_complete else "",
        nb_best_hits=config["nb_best_hits"],
    priority: 999
    conda:
        "envs/cobs.yaml"
    shell:
        """
        ./scripts/benchmark.py --log logs/benchmarks/run_cobs/{wildcards.batch}____{wildcards.qfile}.txt \\
            'cobs query \\
                    {params.load_complete} \\
                    -t {params.kmer_thres} \\
                    -T {threads} \\
                    -i {input.cobs_index} \\
                    -f {input.fa} \\
                | ./scripts/postprocess_cobs.py -n {params.nb_best_hits} \\
                | gzip --fast \\
                > {output.match}'
        """


rule decompress_and_run_cobs:
    """Decompress Cobs index and run Cobs matching
    """
    output:
        match="intermediate/01_match/{batch}____{qfile}.gz",
    input:
        compressed_cobs_index=f"{cobs_dir}/{{batch}}.cobs_classic.xz",
        fa="intermediate/concatenated_query/{qfile}.fa",
        decompressed_indexes_sizes="data/decompressed_indexes_sizes.txt",
    resources:
        max_io_heavy_threads=int(cobs_is_an_IO_heavy_job),
        max_ram_mb=lambda wildcards, input: get_uncompressed_batch_size_in_MB(
            wildcards, input, ignore_RAM, streaming
        ),
    threads: lambda wildcards, input: get_number_of_COBS_threads(
    wildcards, input, predefined_cobs_threads, streaming
)
    params:
        kmer_thres=config["cobs_kmer_thres"],
        decompression_dir=decompression_dir,
        cobs_index=lambda wildcards: f"{decompression_dir}/{wildcards.batch}.cobs_classic",
        cobs_index_tmp=lambda wildcards: f"{decompression_dir}/{wildcards.batch}.cobs_classic.tmp",
        load_complete="--load-complete" if load_complete else "",
        nb_best_hits=config["nb_best_hits"],
        uncompressed_batch_size=get_uncompressed_batch_size,
        streaming=int(streaming),
    conda:
        "envs/cobs.yaml"
    shell:
        """
        if [ {params.streaming} = 1 ]
        then
            ./scripts/benchmark.py --log logs/benchmarks/run_cobs/{wildcards.batch}____{wildcards.qfile}.txt \\
            './scripts/run_cobs_streaming.sh {params.kmer_thres} {threads} "{input.compressed_cobs_index}" {params.uncompressed_batch_size} "{input.fa}" \\
                    | ./scripts/postprocess_cobs.py -n {params.nb_best_hits} \\
                    | gzip --fast\\
                    > {output.match}'
        else
            mkdir -p {params.decompression_dir}
            ./scripts/benchmark.py --log logs/benchmarks/decompress_cobs/{wildcards.batch}____{wildcards.qfile}.txt \\
                'xzcat "{input.compressed_cobs_index}" > "{params.cobs_index_tmp}" \\
                && mv "{params.cobs_index_tmp}" "{params.cobs_index}"'
            ./scripts/benchmark.py --log logs/benchmarks/run_cobs/{wildcards.batch}____{wildcards.qfile}.txt \\
                'cobs query \\
                        {params.load_complete} \\
                        -t {params.kmer_thres} \\
                        -T {threads} \\
                        -i "{params.cobs_index}" \\
                        -f "{input.fa}" \\
                    | ./scripts/postprocess_cobs.py -n {params.nb_best_hits} \\
                    | gzip --fast\\
                    > {output.match}'
            rm -v "{params.cobs_index}"
        fi
        """


rule translate_matches:
    """Translate cobs matches.

    Output:
        ref - read - matches
    """
    output:
        fa="intermediate/02_filter/{qfile}.fa",
    input:
        fa="intermediate/concatenated_query/{qfile}.fa",
        all_matches=[
            f"intermediate/01_match/{batch}____{{qfile}}.gz" for batch in batches
        ],
    conda:
        "envs/minimap2.yaml"
    threads: 1
    log:
        "logs/translate_matches/{qfile}.log",
    params:
        nb_best_hits=config["nb_best_hits"],
    shell:
        """
        ./scripts/benchmark.py --log logs/benchmarks/translate_matches/translate_matches___{wildcards.qfile}.txt \\
            './scripts/filter_queries.py \\
                    -n {params.nb_best_hits} \\
                    -q {input.fa} \\
                    {input.all_matches} \\
                > {output.fa} 2>{log}'
        """


rule batch_align_minimap2:
    output:
        sam="intermediate/03_map/{batch}____{qfile}.sam.gz",
    input:
        qfa="intermediate/02_filter/{qfile}.fa",
        asm=f"{assemblies_dir}/{{batch}}.tar.xz",
    log:
        log="logs/03_map/{batch}____{qfile}.log",
    params:
        minimap_preset=config["minimap_preset"],
        minimap_extra_params=config["minimap_extra_params"],
        pipe="--pipe" if config["prefer_pipe"] else "",
        refs_tmp="intermediate/03_map/{batch}____{qfile}.refs.tmp",
    conda:
        "envs/minimap2.yaml"
    threads: config["minimap_threads"]
    shell:
        """
        xzcat data/661k_batches.txt.xz \\
            | grep {wildcards.batch} \\
            | cut -f2 \\
            > {params.refs_tmp}

        ./scripts/benchmark.py --log logs/benchmarks/batch_align_minimap2/{wildcards.batch}____{wildcards.qfile}.txt \\
            './scripts/batch_align.py \\
                    --minimap-preset {params.minimap_preset} \\
                    --threads {threads} \\
                    --extra-params=\"{params.minimap_extra_params}\" \\
                    --accessions {params.refs_tmp} \\
                    {params.pipe} \\
                    {input.asm} \\
                    {input.qfa} \\
                2>{log} \\
                | {{ grep -Ev "^@" || true; }} \\
                | gzip --fast\\
                > {output.sam}'

        rm -f {params.refs_tmp}
        """


rule aggregate_sams:
    output:
        pseudosam="output/{qfile}.sam_summary.gz",
    input:
        sam=[f"intermediate/03_map/{batch}____{{qfile}}.sam.gz" for batch in batches],
    shell:
        """
        ./scripts/benchmark.py --log logs/benchmarks/aggregate_sams/aggregate_sams___{wildcards.qfile}.txt \\
            './scripts/aggregate_sams.sh {input.sam} \\
                > {output.pseudosam}'
        """


rule final_stats:
    output:
        stats="output/{qfile}.sam_summary.stats",
    input:
        pseudosam="output/{qfile}.sam_summary.gz",
        concatenated_query=f"intermediate/concatenated_query/{get_filename_for_all_queries()}.fa",
    conda:
        "envs/minimap2.yaml"
    shell:
        """
        ./scripts/benchmark.py --log logs/benchmarks/aggregate_sams/final_stats___{wildcards.qfile}.txt \\
            './scripts/final_stats.py {input.concatenated_query} {input.pseudosam} \\
                > {output.stats}'
        """
