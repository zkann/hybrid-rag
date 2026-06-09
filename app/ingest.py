"""Ingestion: turn raw documents into embedded, searchable chunks.

ingest_document() is idempotent on `source`: re-ingesting a path/URL replaces
its chunks, so re-running the seed is safe.
"""

from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .chunking import chunk_text
from .db import get_pool, to_pgvector
from .embeddings import embed_texts

_DOC_SUFFIXES = {".md", ".mdx", ".markdown", ".txt", ".rst"}


def ingest_document(source: str, title: str, text: str) -> int:
    """Insert/replace a document and its chunks. Returns chunk count."""
    chunks = chunk_text(text)
    if not chunks:
        return 0
    vectors = embed_texts(chunks)

    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (source, title) VALUES (%s, %s) "
                "ON CONFLICT (source) DO UPDATE SET title = EXCLUDED.title "
                "RETURNING id",
                (source, title),
            )
            doc_id = cur.fetchone()[0]
            cur.execute("DELETE FROM chunks WHERE document_id = %s", (doc_id,))
            for ord_, (content, vec) in enumerate(zip(chunks, vectors)):
                cur.execute(
                    "INSERT INTO chunks (document_id, ord, content, embedding) "
                    "VALUES (%s, %s, %s, %s::vector)",
                    (doc_id, ord_, content, to_pgvector(vec)),
                )
        conn.commit()
    return len(chunks)


def ingest_markdown_dir(root: str) -> tuple[int, int]:
    """Ingest every markdown/text file under root. Returns (docs, chunks)."""
    root_path = Path(root)
    docs = chunks = 0
    for path in sorted(root_path.rglob("*")):
        if path.suffix.lower() not in _DOC_SUFFIXES or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        rel = str(path.relative_to(root_path))
        n = ingest_document(source=rel, title=path.stem, text=text)
        if n:
            docs += 1
            chunks += n
            print(f"  ingested {rel}: {n} chunks")
    return docs, chunks


def _html_to_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else "untitled"
    main = soup.find("main") or soup.body or soup
    return title, main.get_text("\n", strip=True)


def ingest_urls(urls: list[str]) -> tuple[int, int]:
    docs = chunks = 0
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for url in urls:
            resp = client.get(url)
            resp.raise_for_status()
            title, text = _html_to_text(resp.text)
            n = ingest_document(source=url, title=title, text=text)
            if n:
                docs += 1
                chunks += n
                print(f"  ingested {url}: {n} chunks")
    return docs, chunks
