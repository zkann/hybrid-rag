"""Unit tests for chunking (no DB / no network)."""

from app.chunking import chunk_text


def test_short_text_single_chunk():
    chunks = chunk_text("# Title\n\nA short paragraph.", chunk_tokens=512, overlap=64)
    assert len(chunks) == 1
    assert "short paragraph" in chunks[0]


def test_long_text_windows_with_overlap():
    body = " ".join(f"word{i}" for i in range(2000))
    chunks = chunk_text(body, chunk_tokens=100, overlap=20)
    assert len(chunks) > 1
    # overlap means consecutive chunks share some leading/trailing tokens
    assert any(chunks[0].split()[-1] in chunks[1] for _ in [0])


def test_headings_split_sections():
    text = "# A\n\nalpha content\n\n# B\n\nbeta content"
    chunks = chunk_text(text, chunk_tokens=512, overlap=0)
    joined = "\n".join(chunks)
    assert "alpha" in joined and "beta" in joined
    assert len(chunks) == 2
