"""FastAPI surface: /health, /search (retrieval only), /ask (RAG answer)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .db import close_pool, get_pool
from .generate import generate_answer
from .retrieval import hybrid_search


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_pool()  # bootstrap schema + pool on startup
    yield
    close_pool()


app = FastAPI(title="hybrid-rag", version="0.1.0", lifespan=lifespan)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=50)


class Citation(BaseModel):
    n: int
    source: str
    title: str
    score: float
    snippet: str


class SearchResponse(BaseModel):
    query: str
    results: list[Citation]


class AskResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation]


def _to_citations(hits) -> list[Citation]:
    return [
        Citation(
            n=i,
            source=h.source,
            title=h.title,
            score=h.score,
            snippet=h.content[:280].replace("\n", " ").strip(),
        )
        for i, h in enumerate(hits, start=1)
    ]


@app.get("/health")
def health() -> dict:
    with get_pool().connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM chunks")
        n = cur.fetchone()[0]
    return {"status": "ok", "indexed_chunks": n}


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    hits = hybrid_search(req.query, top_k=req.top_k)
    return SearchResponse(query=req.query, results=_to_citations(hits))


@app.post("/ask", response_model=AskResponse)
def ask(req: SearchRequest) -> AskResponse:
    hits = hybrid_search(req.query, top_k=req.top_k)
    answer = generate_answer(req.query, hits)
    return AskResponse(query=req.query, answer=answer, citations=_to_citations(hits))
