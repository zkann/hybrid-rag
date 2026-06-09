#!/usr/bin/env python3
"""Ingest a corpus into the hybrid-rag index.

Examples:
    python -m scripts.ingest_docs --dir docs_corpus
    python -m scripts.ingest_docs --url https://example.com/docs/page
"""

import argparse
import sys

from app.ingest import ingest_markdown_dir, ingest_urls


def main() -> int:
    p = argparse.ArgumentParser(description="Ingest documents into hybrid-rag.")
    p.add_argument("--dir", help="Directory of markdown/text files to ingest.")
    p.add_argument("--url", action="append", default=[], help="URL(s) to fetch and ingest.")
    args = p.parse_args()

    if not args.dir and not args.url:
        p.error("provide --dir and/or --url")

    docs = chunks = 0
    if args.dir:
        print(f"Ingesting directory: {args.dir}")
        d, c = ingest_markdown_dir(args.dir)
        docs += d
        chunks += c
    if args.url:
        print(f"Ingesting {len(args.url)} URL(s)")
        d, c = ingest_urls(args.url)
        docs += d
        chunks += c

    print(f"\nDone. {docs} documents, {chunks} chunks indexed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
