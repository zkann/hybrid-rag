"""Heading-aware, token-windowed chunking.

We split the document on markdown headings first (so a chunk keeps a coherent
section), then pack each section into overlapping token windows. Token counts
use tiktoken's cl100k_base so windows line up with how the models see text.
"""

import re

import tiktoken

from .config import get_settings

_enc = tiktoken.get_encoding("cl100k_base")
_HEADING = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)


def _split_sections(text: str) -> list[str]:
    """Split on markdown headings, keeping each heading with its body."""
    starts = [m.start() for m in _HEADING.finditer(text)]
    if not starts:
        return [text]
    if starts[0] != 0:
        starts = [0] + starts
    sections = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        section = text[start:end].strip()
        if section:
            sections.append(section)
    return sections


def _window(tokens: list[int], size: int, overlap: int) -> list[list[int]]:
    if len(tokens) <= size:
        return [tokens]
    windows = []
    start = 0
    step = max(1, size - overlap)
    while start < len(tokens):
        windows.append(tokens[start : start + size])
        if start + size >= len(tokens):
            break
        start += step
    return windows


def chunk_text(text: str, chunk_tokens: int | None = None, overlap: int | None = None) -> list[str]:
    s = get_settings()
    size = chunk_tokens or s.chunk_tokens
    ov = overlap if overlap is not None else s.chunk_overlap
    chunks: list[str] = []
    for section in _split_sections(text):
        toks = _enc.encode(section)
        for win in _window(toks, size, ov):
            piece = _enc.decode(win).strip()
            if piece:
                chunks.append(piece)
    return chunks
