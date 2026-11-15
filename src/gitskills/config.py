"""Paths and constants shared by every module.

The dataset location is read from the GITSKILLS_DB environment variable so the
same code runs on the 277 MB sample and on the 41 GB full SQLite file.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
TABLES = RESULTS / "tables"

DEFAULT_DB = DATA_RAW / "agent_skills_sample.db"


def db_path() -> Path:
    return Path(os.environ.get("GITSKILLS_DB", DEFAULT_DB))


# Public date of Anthropic's Agent Skills specification. Files whose first
# commit predates it are mostly unrelated `skill.md` files (see paper, App. A).
FORMAT_RELEASE = "2025-10-01"

# Snapshot used by the dataset (cite it in the paper, as the CFP requires).
SNAPSHOT = "GitSkills July 2026 (Zenodo 10.5281/zenodo.21875637)"

# Download locations listed in the paper and on the challenge page.
SAMPLE_ZIP_URL = (
    "https://github.com/giuseppedestefanis/gitskills-sample/raw/main/agent_skills_sample.zip"
)
ZENODO_RECORD = "21875637"
HF_REPO_ID = "mvaccargiu/gitskills"

# Agent Skills specification limits for the front matter.
SPEC_NAME_MAX = 64
SPEC_DESCRIPTION_MAX = 1024

for _p in (DATA_RAW, DATA_PROCESSED, FIGURES, TABLES):
    _p.mkdir(parents=True, exist_ok=True)
