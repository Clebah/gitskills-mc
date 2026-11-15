"""Cleaning and population definitions.

The dataset is deliberately inclusive (paper, App. A): it keeps case variants
such as `skill.md`, files that predate the format, symlinks, malformed front
matter and the few files whose content changed during collection. This module
turns those caveats into explicit flags, so every analysis can state which
population it uses and report sensitivity to the choice.

Two units of analysis exist:

* occurrence: one row of `artifacts` (a file at a repo/path) -> adoption, reuse
* skill: one distinct content (`dedup_primary = 1`) -> text, structure, security
"""

from __future__ import annotations

import pandas as pd

from .config import FORMAT_RELEASE
from .db import query

COPIES_SQL = """
SELECT file_sha,
       COUNT(*)                                   AS copies,
       COUNT(DISTINCT a.repo_full_name)           AS n_repos,
       COUNT(DISTINCT r.owner)                    AS n_owners,
       SUM(a.location_class = 'canonical')        AS n_canonical,
       SUM(a.location_class = 'skills-dir')       AS n_skills_dir,
       SUM(a.location_class = 'other')            AS n_other
FROM artifacts a LEFT JOIN repos r ON r.full_name = a.repo_full_name
GROUP BY file_sha
"""

OCCURRENCES_SQL = """
SELECT a.repo_full_name, a.path, a.filename, a.location_class, a.file_sha,
       a.dedup_primary, r.owner, r.stars, r.forks, r.language, r.license,
       r.created_at AS repo_created_at, r.pushed_at AS repo_pushed_at
FROM artifacts a LEFT JOIN repos r ON r.full_name = a.repo_full_name
"""

SKILL_COLUMNS = """
a.repo_full_name, a.path, a.filename, a.location_class, a.file_sha,
a.frontmatter_valid, a.name, a.description, a.body_chars,
a.content_sha_ok, a.sibling_count, a.sibling_bytes, a.has_scripts,
a.has_references, a.composition_fetched, a.composition_truncated,
a.history_fetched, a.first_commit_at, a.last_commit_at, a.commit_count,
a.first_commit_author, a.first_commit_author_type,
a.last_commit_author, a.last_commit_author_type,
a.first_commit_message, a.last_commit_message,
r.owner, r.stars, r.forks, r.language, r.created_at AS repo_created_at,
r.pushed_at AS repo_pushed_at
"""


def copies() -> pd.DataFrame:
    """Copy statistics per distinct content (file_sha)."""
    return query(COPIES_SQL)


def occurrences() -> pd.DataFrame:
    """Every file occurrence with its repository metadata (no text)."""
    df = query(OCCURRENCES_SQL)
    for c in ("repo_created_at", "repo_pushed_at"):
        df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    return df


def skills(with_content: bool = False) -> pd.DataFrame:
    """One row per distinct content (the representative), with quality flags.

    `with_content=True` loads the full SKILL.md text: fine on the sample,
    on the full dataset use `gitskills.features.build_features` instead.
    """
    cols = SKILL_COLUMNS + (", a.content" if with_content else "")
    df = query(
        f"SELECT {cols} FROM artifacts a LEFT JOIN repos r "
        "ON r.full_name = a.repo_full_name WHERE a.dedup_primary = 1"
    )
    df = df.merge(copies(), on="file_sha", how="left")
    return add_flags(df)


def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ("first_commit_at", "last_commit_at", "repo_created_at", "repo_pushed_at"):
        if c in df:
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    df["exact_basename"] = df["filename"].eq("SKILL.md")
    df["fm_valid"] = df["frontmatter_valid"].eq(1)
    df["sha_ok"] = df["content_sha_ok"].isin([1, 2])
    df["pre_format"] = df["first_commit_at"] < pd.Timestamp(FORMAT_RELEASE, tz="UTC")
    if "content" in df:
        df["is_symlink_like"] = df["content"].fillna("").map(_looks_like_symlink)
    df["has_history"] = df["history_fetched"].eq(1)
    df["first_month"] = df["first_commit_at"].dt.tz_localize(None).dt.to_period("M")
    return df


def _looks_like_symlink(text: str) -> bool:
    """A symlinked SKILL.md stores the link target (a short single-line path)."""
    t = text.strip()
    return 0 < len(t) < 256 and "\n" not in t and ("/" in t or t.endswith(".md"))


def strict(df: pd.DataFrame) -> pd.DataFrame:
    """Conservative population: real Agent Skills, as the specification defines them.

    Exact `SKILL.md` basename, valid front matter, verified content, not a
    symlink, and not first committed before the format existed.
    """
    mask = df["exact_basename"] & df["fm_valid"] & df["sha_ok"] & ~df["pre_format"].fillna(False)
    if "is_symlink_like" in df:
        mask &= ~df["is_symlink_like"]
    return df[mask]


def population_report(df: pd.DataFrame) -> pd.DataFrame:
    """How many skills each filter removes: report it in the paper."""
    steps = [
        ("all representatives", pd.Series(True, index=df.index)),
        ("exact basename SKILL.md", df["exact_basename"]),
        ("valid front matter", df["fm_valid"]),
        ("content hash verified", df["sha_ok"]),
        ("not pre-format", ~df["pre_format"].fillna(False)),
    ]
    if "is_symlink_like" in df:
        steps.append(("not a symlink", ~df["is_symlink_like"]))
    rows, mask = [], pd.Series(True, index=df.index)
    for label, m in steps:
        mask &= m
        rows.append((label, int(mask.sum()), round(100 * mask.mean(), 2)))
    return pd.DataFrame(rows, columns=["filter (cumulative)", "skills", "% of all"])


def load_skills() -> pd.DataFrame:
    """Processed skills table written by `make features`."""
    from .config import DATA_PROCESSED

    df = pd.read_parquet(DATA_PROCESSED / "skills.parquet")
    df["first_month"] = df["first_commit_at"].dt.tz_localize(None).dt.to_period("M")
    return df


def load_occurrences() -> pd.DataFrame:
    from .config import DATA_PROCESSED

    return pd.read_parquet(DATA_PROCESSED / "occurrences.parquet")
