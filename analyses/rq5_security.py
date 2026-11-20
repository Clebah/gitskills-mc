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

# %% Additions vs removals: exact McNemar test per risk category.
# Under random drift, a variant is as likely to add a capability as to remove it.
from scipy.stats import binomtest

if not drift.empty:
    rows = []
    for c in risk_cols:
        added, removed = int(drift[f"added_{c}"].sum()), int(drift[f"removed_{c}"].sum())
        p = binomtest(added, added + removed, 0.5).pvalue if added + removed else float("nan")
        rows.append({"capability": c, "added": added, "removed": removed, "mcnemar_p": p})
    save_table(pd.DataFrame(rows), "rq5_mcnemar_added_vs_removed")

# %% Wilson 95% interval for the share of variants that add >= 1 risky capability
from statsmodels.stats.proportion import proportion_confint

if not drift.empty:
    k, n = int(drift["any_added"].sum()), len(drift)
    lo, hi = proportion_confint(k, n, method="wilson")
    print(f"share adding risk: {k / n:.3f} (95% Wilson CI {lo:.3f}-{hi:.3f}), n={n}")

# %% Logistic regression: which variants add risk?
# Outcome: variant adds >= 1 risky capability absent from its family reference.
# Predictors: popularity of the reference (log copies), family size, whether the
# variant crosses owners, whether it bundles scripts, and assistant authorship.
import numpy as np
import statsmodels.formula.api as smf

if not drift.empty:
    meta = skills.set_index("file_sha")
    d = drift.join(meta[["n_owners", "has_scripts", "first_commit_ai"]], on="file_sha")
    d["family_size"] = d.groupby("family")["file_sha"].transform("size") + 1
    d = d.assign(
        added=d["any_added"].astype(int),
        log_ref_copies=np.log1p(d["ref_copies"]),
        log_family_size=np.log(d["family_size"]),
        cross_owner=(d["n_owners"] > 1).astype(int),
        has_scripts=d["has_scripts"].fillna(0).astype(int),
        ai_authored=d["first_commit_ai"].notna().astype(int),
    )
    model = smf.logit(
        "added ~ log_ref_copies + log_family_size + cross_owner + has_scripts + ai_authored", data=d
    ).fit(disp=False)
    print(model.summary())
    or_table = pd.DataFrame({
        "odds_ratio": np.exp(model.params), "ci_low": np.exp(model.conf_int()[0]),
        "ci_high": np.exp(model.conf_int()[1]), "p": model.pvalues,
    }).reset_index(names="term")
    save_table(or_table, "rq5_logit_odds_ratios")
