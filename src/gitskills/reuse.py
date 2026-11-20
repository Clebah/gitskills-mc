"""Reuse without a package manager (RQ3) and variant drift (RQ5b).

Exact reuse = identical `file_sha`. Near-duplicate reuse = different hashes
that are edits of the same skill; we group them into *families* either by the
normalized front-matter name (cheap baseline) or by MinHash/LSH over the body
(optional dependency `datasketch`).
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


def gini(x) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    if x.size == 0 or x.sum() == 0:
        return float("nan")
    n = x.size
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def concentration(copies: pd.Series) -> dict[str, float]:
    """How concentrated is reuse? (long tail vs a few mass-copied templates)."""
    c = copies.sort_values(ascending=False).to_numpy()
    total = c.sum()
    return {
        "distinct_contents": int(c.size),
        "occurrences": int(total),
        "share_singletons": float((c == 1).mean()),
        "share_occ_duplicated": float((total - c.size) / total),
        "top1pct_share_of_occ": float(c[: max(1, c.size // 100)].sum() / total),
        "top10_share_of_occ": float(c[:10].sum() / total),
        "gini": gini(c),
        "max_copies": int(c.max()),
    }


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None
    n = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return n or None


def name_families(skills: pd.DataFrame, min_variants: int = 2) -> pd.DataFrame:
    """Baseline families: distinct contents sharing a normalized name."""
    df = skills.assign(family=skills["name"].map(normalize_name)).dropna(subset=["family"])
    sizes = df.groupby("family")["file_sha"].transform("nunique")
    return df[sizes >= min_variants]


def minhash_families(
    skills: pd.DataFrame, text_col: str = "content", threshold: float = 0.8, num_perm: int = 128
) -> pd.Series:
    """Cluster near-duplicate bodies with MinHash LSH. Returns a family id per row."""
    from datasketch import MinHash, MinHashLSH

    def shingles(t: str, k: int = 5):
        toks = re.findall(r"\w+", (t or "").lower())
        return {" ".join(toks[i : i + k]) for i in range(max(1, len(toks) - k + 1))}

    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    hashes: dict[str, MinHash] = {}
    for idx, text in skills[text_col].items():
        m = MinHash(num_perm=num_perm)
        for s in shingles(text):
            m.update(s.encode())
        hashes[str(idx)] = m
        lsh.insert(str(idx), m)

    parent = {k: k for k in hashes}

    def find(k: str) -> str:
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for key, m in hashes.items():
        for other in lsh.query(m):
            a, b = find(key), find(other)
            if a != b:
                parent[b] = a
    fam = {k: find(k) for k in hashes}
    return pd.Series([fam[str(i)] for i in skills.index], index=skills.index, name="family")


def variant_drift(families: pd.DataFrame, risk_cols: list[str], family_col: str = "family") -> pd.DataFrame:
    """Compare each variant with its family's most-copied member (origin proxy).

    Returns, per variant, which risk categories it has that the reference lacks
    (`added_*`). The reference is a proxy: the dataset does not record which
    copy is the original, so report this as an assumption.
    """
    rows = []
    for fam, g in families.groupby(family_col):
        ref = g.sort_values(["copies", "first_commit_at"], ascending=[False, True]).iloc[0]
        for _, v in g.iterrows():
            if v["file_sha"] == ref["file_sha"]:
                continue
            row = {"family": fam, "file_sha": v["file_sha"], "ref_sha": ref["file_sha"],
                   "copies": v["copies"], "ref_copies": ref["copies"]}
            for c in risk_cols:
                row[f"added_{c}"] = bool(v[c]) and not bool(ref[c])
                row[f"removed_{c}"] = bool(ref[c]) and not bool(v[c])
            rows.append(row)
    out = pd.DataFrame(rows)
    if not out.empty:
        out["any_added"] = out.filter(like="added_").any(axis=1)
    return out
