"""Download GitSkills.

    python scripts/download.py sample   # 13k-skill sample from GitHub (~87 MB zip)
    python scripts/download.py zenodo   # full SQLite from Zenodo (~41-44 GB)
    python scripts/download.py hf       # Parquet mirror from Hugging Face

Start with the sample: every query written against it runs unchanged on the
full database (same schema and invariants, per the dataset authors).
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gitskills.config import DATA_RAW, HF_REPO_ID, SAMPLE_ZIP_URL, ZENODO_RECORD  # noqa: E402


def fetch(url: str, dest: Path) -> Path:
    if dest.exists():
        print(f"exists: {dest}")
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    start = tmp.stat().st_size if tmp.exists() else 0
    headers = {"Range": f"bytes={start}-"} if start else {}
    with requests.get(url, stream=True, timeout=60, headers=headers) as r:
        r.raise_for_status()
        mode = "ab" if r.status_code == 206 else "wb"
        total = int(r.headers.get("content-length", 0)) + (start if mode == "ab" else 0)
        done = start if mode == "ab" else 0
        with open(tmp, mode) as f:
            for block in r.iter_content(chunk_size=1 << 22):
                f.write(block)
                done += len(block)
                if total:
                    print(f"\r{dest.name}: {done / total:6.1%}", end="", flush=True)
    print()
    tmp.rename(dest)
    return dest


def sample() -> None:
    z = fetch(SAMPLE_ZIP_URL, DATA_RAW / "agent_skills_sample.zip")
    with zipfile.ZipFile(z) as zf:
        zf.extractall(DATA_RAW)
    print(f"ok: {DATA_RAW / 'agent_skills_sample.db'}")


def zenodo() -> None:
    meta = requests.get(f"https://zenodo.org/api/records/{ZENODO_RECORD}", timeout=60).json()
    for f in meta.get("files", []):
        print(f"{f['key']}  {f['size'] / 1e9:.1f} GB")
        fetch(f["links"]["self"], DATA_RAW / f["key"])
    print("If the file is compressed, decompress it and point GITSKILLS_DB to the .db file.")


def hf() -> None:
    from huggingface_hub import snapshot_download

    path = snapshot_download(HF_REPO_ID, repo_type="dataset", local_dir=DATA_RAW / "parquet")
    print(f"ok: {path}  (query with duckdb: SELECT ... FROM 'data/raw/parquet/<table>/*.parquet')")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "sample"
    {"sample": sample, "zenodo": zenodo, "hf": hf}[target]()
