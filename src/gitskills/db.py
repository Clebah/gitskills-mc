"""Read-only access to the GitSkills SQLite database.

Everything goes through SQL so that heavy filtering happens inside SQLite.
For the full dataset (~41 GB) prefer `iter_query` with a chunk size, or push
aggregations into SQL, instead of loading `content` columns into memory.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pandas as pd

from .config import db_path


@contextmanager
def connect(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    p = Path(path) if path else db_path()
    if not p.exists():
        raise FileNotFoundError(
            f"Database not found at {p}. Run `make sample` or set GITSKILLS_DB."
        )
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        yield conn
    finally:
        conn.close()


def query(sql: str, params: tuple | dict = (), path: Path | str | None = None) -> pd.DataFrame:
    with connect(path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def iter_query(
    sql: str, chunksize: int = 50_000, params: tuple | dict = (), path: Path | str | None = None
) -> Iterator[pd.DataFrame]:
    with connect(path) as conn:
        yield from pd.read_sql_query(sql, conn, params=params, chunksize=chunksize)


def table_counts(path: Path | str | None = None) -> pd.DataFrame:
    tables = ["artifacts", "repos", "artifact_siblings", "mining_runs"]
    with connect(path) as conn:
        rows = [(t, conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in tables]
    return pd.DataFrame(rows, columns=["table", "rows"])
