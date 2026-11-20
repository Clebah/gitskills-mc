"""Adoption over time and adopter profile (RQ1, RQ2a).

Dates come from `first_commit_at`, which exists only for the history sample:
skills in standard locations plus a size-stratified sample of the rest. On the
official sample, coverage is ~100% for `canonical` but only ~11% for
`skills-dir` and `other`; check `history_coverage` on the full data. Time series therefore either restrict to
standard locations or reweight the `other` stratum; never silently mix them.
"""

from __future__ import annotations

import pandas as pd

from .config import FORMAT_RELEASE


def monthly_cohorts(skills: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    df = skills[skills["has_history"] & skills["first_month"].notna()]
    df = df[df["first_commit_at"] >= pd.Timestamp(FORMAT_RELEASE, tz="UTC")]
    keys = ["first_month"] + ([by] if by else [])
    out = df.groupby(keys).size().rename("new_skills").reset_index()
    if by:
        out["share"] = out["new_skills"] / out.groupby("first_month")["new_skills"].transform("sum")
    return out


def history_coverage(skills: pd.DataFrame) -> pd.DataFrame:
    """Share of skills with history per location class (sampling design)."""
    return (skills.groupby("location_class")["has_history"]
            .agg(skills="size", with_history="sum", share="mean").reset_index())


def adopter_profile(occ: pd.DataFrame) -> pd.DataFrame:
    """One row per repository that holds at least one SKILL.md."""
    g = occ.groupby("repo_full_name")
    prof = g.agg(
        owner=("owner", "first"), stars=("stars", "first"), language=("language", "first"),
        repo_created_at=("repo_created_at", "first"), repo_pushed_at=("repo_pushed_at", "first"),
        n_skill_files=("path", "size"),
        n_canonical=("location_class", lambda s: (s == "canonical").sum()),
    ).reset_index()
    prof["catalog_like"] = prof["n_skill_files"] >= 20  # heuristic: skill catalogs / collections
    return prof
