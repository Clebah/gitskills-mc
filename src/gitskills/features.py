"""Per-skill features derived from SKILL.md text and commit metadata.

`extract(text)` works on a single string, so it is unit-testable;
`build_features()` streams representatives from SQLite in chunks and writes
`data/processed/skill_features.parquet`, which every RQ script reads.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import yaml

from . import patterns as P
from .config import DATA_PROCESSED, SPEC_DESCRIPTION_MAX, SPEC_NAME_MAX
from .db import iter_query

FRONT_MATTER = re.compile(r"\A﻿?---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)


def split_front_matter(text: str) -> tuple[dict[str, Any] | None, str]:
    """Return (front-matter dict or None, body)."""
    m = FRONT_MATTER.match(text or "")
    if not m:
        return None, text or ""
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        fm = None
    return (fm if isinstance(fm, dict) else None), text[m.end():]


def extract(text: str) -> dict[str, Any]:
    text = text or ""
    fm, body = split_front_matter(text)
    fm = fm or {}
    name = str(fm.get("name") or "")
    desc = str(fm.get("description") or "")
    keys = set(map(str, fm.keys()))

    words = re.findall(r"\w+", body)
    lines = body.splitlines()
    fences = P.CODE_FENCE.findall(body)
    lower = text.lower()

    f: dict[str, Any] = {
        # front matter / spec compliance
        "fm_keys": ",".join(sorted(keys)),
        "fm_extra_keys": len(keys - P.SPEC_KEYS),
        "has_allowed_tools": "allowed-tools" in keys,
        "name_spec_ok": bool(P.SPEC_NAME.match(name)) and len(name) <= SPEC_NAME_MAX,
        "desc_chars": len(desc),
        "desc_words": len(desc.split()),
        "desc_spec_ok": 0 < len(desc) <= SPEC_DESCRIPTION_MAX and "<" not in desc,
        "desc_has_trigger": bool(P.TRIGGER_PHRASES.search(desc)),
        # body structure
        "body_words": len(words),
        "body_lines": len(lines),
        "n_headings": len(P.HEADING.findall(body)),
        "n_list_items": len(P.LIST_ITEM.findall(body)),
        "n_code_blocks": len(fences) // 2,
        "n_shell_blocks": sum(1 for lang in fences if lang.lower() in {"bash", "sh", "shell", "zsh", "console"}),
        "n_urls": len(P.URL.findall(body)),
        "n_directives": len(P.DIRECTIVES.findall(body)),
        "directives_per_100w": 100 * len(P.DIRECTIVES.findall(body)) / max(len(words), 1),
        "non_ascii_ratio": sum(ord(c) > 127 for c in body) / max(len(body), 1),
    }
    tools = [k for k, rx in P.COMPILED_TOOLS.items() if rx.search(lower)]
    f["tools_named"] = ",".join(tools)
    f["n_tools_named"] = len(tools)
    for k, rx in P.COMPILED_RISKS.items():
        f[f"risk_{k}"] = bool(rx.search(text))
    f["n_risk_categories"] = sum(f[f"risk_{k}"] for k in P.COMPILED_RISKS)
    return f


def ai_coauthor(message: str | None) -> str | None:
    """Name of the AI assistant credited in a Co-authored-by trailer, if any."""
    if not isinstance(message, str) or not message:
        return None
    m = P.AI_TRAILER.search(message)
    return m.group(1).lower() if m else None


def detect_language(text: str) -> str | None:
    """Natural language of the body (optional dependency `langdetect`)."""
    try:
        from langdetect import DetectorFactory, detect
    except ImportError:
        return None
    DetectorFactory.seed = 0
    _, body = split_front_matter(text)
    body = P.CODE_FENCE.sub(" ", body)[:4000]
    try:
        return detect(body) if len(body.split()) >= 20 else None
    except Exception:
        return None


def _extract_many(texts: list[str]) -> list[dict[str, Any]]:
    return [extract(t) for t in texts]


def build_features(chunksize: int = 20_000, language: bool = False, workers: int | None = None) -> pd.DataFrame:
    """Stream representatives and extract features (parallel over CPU cores)."""
    import os
    from concurrent.futures import ProcessPoolExecutor

    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    sql = """
        SELECT file_sha, content, first_commit_message, last_commit_message,
               first_commit_author_type, last_commit_author_type
        FROM artifacts WHERE dedup_primary = 1
    """
    parts = []
    pool = ProcessPoolExecutor(workers) if workers > 1 else None
    for chunk in iter_query(sql, chunksize=chunksize):
        texts = chunk["content"].fillna("").tolist()
        if pool:
            step = max(1, len(texts) // (workers * 4))
            batches = [texts[i : i + step] for i in range(0, len(texts), step)]
            rows = [r for batch in pool.map(_extract_many, batches) for r in batch]
        else:
            rows = _extract_many(texts)
        feats = pd.DataFrame(rows)
        feats.insert(0, "file_sha", chunk["file_sha"].values)
        feats["first_commit_ai"] = chunk["first_commit_message"].map(ai_coauthor).values
        feats["last_commit_ai"] = chunk["last_commit_message"].map(ai_coauthor).values
        feats["first_commit_bot"] = chunk["first_commit_author_type"].eq("Bot").values
        if language:
            feats["language_nl"] = chunk["content"].map(detect_language).values
        parts.append(feats)
        print(f"  features: {sum(map(len, parts)):,} skills", flush=True)
    if pool:
        pool.shutdown()
    out = pd.concat(parts, ignore_index=True)
    out.to_parquet(DATA_PROCESSED / "skill_features.parquet", index=False)
    return out


def load_features() -> pd.DataFrame:
    path = DATA_PROCESSED / "skill_features.parquet"
    if not path.exists():
        raise FileNotFoundError("Run `make features` first.")
    return pd.read_parquet(path)
