"""OpenAI embeddings. Batched; returns plain python lists."""

from openai import OpenAI

from .config import get_settings

_client: OpenAI | None = None


def _client_() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_settings().openai_api_key)
    return _client


def embed_texts(texts: list[str], batch_size: int = 128) -> list[list[float]]:
    s = get_settings()
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = _client_().embeddings.create(model=s.embedding_model, input=batch)
        out.extend(d.embedding for d in resp.data)
    return out


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
