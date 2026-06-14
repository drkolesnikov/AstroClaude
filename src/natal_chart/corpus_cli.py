import argparse

from natal_chart.corpus import ingest_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the depth corpus into a local index.")
    parser.add_argument("--sources", default="corpus/sources", help="Flat corpus source directory.")
    parser.add_argument("--index", default="corpus/index", help="Local index output directory.")
    args = parser.parse_args()

    result = ingest_corpus(source_dir=args.sources, index_dir=args.index)
    print(
        f"indexed {result.indexed_sources} sources into {result.chunks_indexed} chunks "
        f"at {result.index_path}"
    )
