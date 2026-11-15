"""Clean + derive features once; every analysis reads the parquet outputs.

    GITSKILLS_DB=data/raw/agent_skills_sample.db python scripts/build_features.py [--language]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills import clean, features  # noqa: E402
from gitskills.config import DATA_PROCESSED, db_path  # noqa: E402

if __name__ == "__main__":
    print(f"database: {db_path()}")
    print("1/3 skills (representatives + copy counts + flags)")
    sk = clean.skills(with_content=False)
    print("2/3 text features")
    feats = features.build_features(language="--language" in sys.argv)
    sk = sk.merge(feats, on="file_sha", how="left")
    # symlink flag needs content: derive it cheaply from body size + features
    sk["is_symlink_like"] = (sk["body_lines"].fillna(0) <= 1) & (sk["n_headings"].fillna(0) == 0) & ~sk["fm_valid"]
    sk = sk.drop(columns=["first_month"]).assign(first_month=sk["first_month"].astype(str))
    sk.to_parquet(DATA_PROCESSED / "skills.parquet", index=False)
    print("3/3 occurrences")
    clean.occurrences().to_parquet(DATA_PROCESSED / "occurrences.parquet", index=False)
    print(clean.population_report(sk).to_string(index=False))
    print(f"done -> {DATA_PROCESSED}")
