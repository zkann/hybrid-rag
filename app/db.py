"""Postgres access: schema bootstrap + a pgvector-aware connection pool."""

from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from .config import get_settings

_SCHEMA = (Path(__file__).resolve().parent.parent / "sql" / "001_schema.sql").read_text()

_pool: ConnectionPool | None = None


def _configure(conn: psycopg.Connection) -> None:
    # Teaches psycopg to adapt python lists <-> pgvector. Requires the
    # `vector` extension to already exist, which ensure_schema() guarantees.
    register_vector(conn)


def ensure_schema() -> None:
    """Apply the schema with a plain connection before the pool comes up,
    so the vector type exists when register_vector runs per-connection."""
    s = get_settings()
    with psycopg.connect(s.database_url, autocommit=True) as conn:
        conn.execute(_SCHEMA)


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        ensure_schema()
        s = get_settings()
        _pool = ConnectionPool(
            s.database_url,
            min_size=1,
            max_size=10,
            configure=_configure,
            open=True,
        )
    return _pool


def to_pgvector(vec) -> str:
    """Render an embedding as a pgvector text literal, e.g. '[0.1,0.2,...]'.
    Paired with an explicit ::vector cast in SQL so it never gets sent as a
    plain float array (which the <=> operator rejects)."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
