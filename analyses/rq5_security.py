# %% [markdown]
# # RQ5 — Maintenance and trust
# * RQ5.1 How often do skills instruct risky capabilities (pipe-to-shell,
#   remote fetch, destructive fs, privilege, secrets, safety bypass), and
#   how widely are those skills copied?
# * RQ5.2 How often do skills bundle executable scripts, and with which
#   languages?
# * RQ5.3 Do modified copies (variants) of widely reused skills add risky
#   capabilities absent from the most-copied member (supply-chain analog)?
# * RQ5.4 Staleness: time between the skill's last commit and the repo's last push.

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src") if "__file__" in dir() else "../src")
import pandas as pd

from gitskills import clean, db, reuse
from gitskills.patterns import SCRIPT_EXTENSIONS
from gitskills.plots import save_table

skills = clean.strict(clean.load_skills())
risk_cols = [c for c in skills.columns if c.startswith("risk_")]

# %% Prevalence of risky capabilities, weighted by copies (exposure)
prev = pd.DataFrame({
    "share_of_skills": skills[risk_cols].mean(),
    "share_of_occurrences": skills[risk_cols].mul(skills["copies"], axis=0).sum() / skills["copies"].sum(),
}).reset_index(names="capability")
save_table(prev, "rq5_risk_prevalence")

# %% Bundled scripts by extension
sib = db.query("""
    SELECT s.entry_name, s.entry_size FROM artifact_siblings s
    JOIN artifacts a ON a.repo_full_name = s.repo_full_name AND a.path = s.artifact_path
    WHERE a.dedup_primary = 1 AND s.entry_type = 'file'
""")
sib["ext"] = sib["entry_name"].str.extract(r"(\.[A-Za-z0-9]+)$")[0].str.lower()
sib["is_script"] = sib["ext"].isin(SCRIPT_EXTENSIONS)
save_table(sib[sib["is_script"]]["ext"].value_counts().rename("files").reset_index(), "rq5_script_extensions")

# %% Variant drift within name families
fam = reuse.name_families(skills)
drift = reuse.variant_drift(fam, risk_cols)
if not drift.empty:
    summary = drift.filter(like="added_").mean().rename("share_of_variants").reset_index()
    save_table(summary, "rq5_variant_added_risk")
    print(f"variants adding >=1 risky capability: {drift['any_added'].mean():.1%} of {len(drift)}")

# %% Staleness
h = skills[skills["has_history"]].copy()
h["days_since_skill_edit_at_last_push"] = (h["repo_pushed_at"] - h["last_commit_at"]).dt.days
save_table(h["days_since_skill_edit_at_last_push"].describe().reset_index(), "rq5_staleness")
