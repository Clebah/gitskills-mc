"""Generate the Jupyter notebooks in notebooks/ (one per methodology step / RQ).

    python scripts/build_notebooks.py          # writes notebooks/*.ipynb (no outputs)
    jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

The notebooks read data/processed/*.parquet, so run `make features` first.
"""

from pathlib import Path

import nbformat as nbf

OUT = Path(__file__).resolve().parents[1] / "notebooks"
SETUP = """import os, sys
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("GITSKILLS_DB", str(ROOT / "data/raw/agent_skills_release.db"))
import numpy as np, pandas as pd, matplotlib.pyplot as plt
pd.set_option("display.max_colwidth", 80)
from gitskills import clean, db, reuse, adoption, patterns
from gitskills.plots import save, save_table
print("database:", os.environ["GITSKILLS_DB"])"""


def nb(cells):
    book = nbf.v4.new_notebook()
    book.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    book.cells = [nbf.v4.new_markdown_cell(c[3:]) if c.startswith("md:") else nbf.v4.new_code_cell(c) for c in cells]
    return book


NOTEBOOKS = {
"01_data_and_cleaning.ipynb": [
"""md:# 1. Data selection, collection and cleaning

**Methodology step 2 (MSR): selection and collection of data.**

* **Source:** GitSkills, July 2026 snapshot (Zenodo 10.5281/zenodo.21875637): every `SKILL.md` file found by GitHub code search, with repository metadata, bundled files and sampled commit history.
* **Units of analysis:** an *occurrence* is one file at one repository path (used for adoption and reuse); a *skill* is one distinct content, identified by its git blob hash (used for text and security analyses).
* **Selection criteria:** the *strict* population keeps skills with the exact `SKILL.md` basename, valid front matter, a verified content hash, no symlink, and a first commit on or after October 2025, when the format was released.
* **Quality validation:** we report how many skills each filter removes and how complete the commit history is per location class.""",
SETUP,
"""md:## 1.1 Dataset size""",
"""counts = db.table_counts()
counts""",
"""md:## 1.2 Load the processed tables
`scripts/build_features.py` streams the database once and writes one row per skill (with features) and one row per occurrence.""",
"""skills = clean.load_skills()
occ = clean.load_occurrences()
print(f"{len(skills):,} distinct skills, {len(occ):,} occurrences, {occ.repo_full_name.nunique():,} repositories")""",
"""md:## 1.3 Selection criteria: the strict population
Each row applies one more filter (cumulative).""",
"""pop = clean.population_report(skills)
save_table(pop, "eda_population_filters")
pop""",
"""md:## 1.4 Where skill files live
`canonical` = `.claude/skills/<name>/SKILL.md`; `skills-dir` = any other `skills/` folder; `other` = anywhere else.""",
"""occ["location_class"].value_counts(normalize=True).rename("share").to_frame()""",
"""occ["filename"].value_counts().head(10).rename("files").to_frame()""",
"""md:## 1.5 Quality: commit-history coverage
Dates exist only for a sample. Time series use only location classes with near-complete coverage.""",
"""cov = adoption.history_coverage(clean.strict(skills))
save_table(cov, "rq1_history_coverage")
cov""",
"""md:## 1.6 Exploratory view: copies per skill and body length""",
"""fig, axes = plt.subplots(1, 2, figsize=(7, 2.6))
vc = skills["copies"].value_counts().sort_index()
axes[0].loglog(vc.index, vc.values, ".", ms=3)
axes[0].set(xlabel="copies of a distinct skill", ylabel="# skills")
b = skills["body_chars"].dropna(); b = b[b > 0]
axes[1].hist(np.log10(b), bins=50)
axes[1].set(xlabel="log10(body characters)", ylabel="# skills")
plt.tight_layout(); plt.show()""",
],
"02_rq1_adoption_and_authorship.ipynb": [
"""md:# 2. RQ1: Adoption and agent authorship

**Methodology step 3: quantitative descriptive analysis.**

* RQ1.1 How fast did the format spread after October 2025?
* RQ1.2 What share of skills were first committed with an AI assistant credited as co-author (a `Co-authored-by` trailer) or by a bot account?

Proportions are reported with 95% Wilson confidence intervals.""",
SETUP + "\nfrom statsmodels.stats.proportion import proportion_confint",
"""skills = clean.strict(clean.load_skills())
cov = adoption.history_coverage(skills)
complete = cov.loc[cov["share"] >= 0.9, "location_class"].tolist()
print("location classes with complete history:", complete)""",
"""md:## 2.1 New skills per month (complete-history classes only)""",
"""std = skills[skills["location_class"].isin(complete)]
cohorts = adoption.monthly_cohorts(std)
ax = cohorts.set_index("first_month")["new_skills"].plot(marker=".", figsize=(6, 2.6))
ax.set_ylabel("new distinct skills"); plt.show()
cohorts""",
"""md:## 2.2 Assistant authorship""",
"""h = skills[skills["has_history"]].copy()
h["ai_first"] = h["first_commit_ai"].notna() | h["first_commit_bot"]
k, n = int(h["ai_first"].sum()), len(h)
lo, hi = proportion_confint(k, n, method="wilson")
print(f"first commit by an assistant or bot: {k:,}/{n:,} = {k/n:.1%} (95% CI {lo:.1%}-{hi:.1%})")""",
"""h["first_commit_ai"].value_counts().rename("skills").to_frame()""",
"""by_month = h.groupby("first_month")["ai_first"].agg(skills="size", share="mean")
ax = by_month["share"].plot(marker=".", figsize=(6, 2.6)); ax.set_ylabel("share assistant-authored"); plt.show()
by_month""",
],
"03_rq3_reuse.ipynb": [
"""md:# 3. RQ3: Reuse without a package manager

**Methodology step 3: quantitative analysis.**

* RQ3.1 How concentrated is reuse? Gini coefficient and share of occurrences held by the top 1% of skills.
* RQ3.2 Does copying cross owners (ecosystem reuse) or stay within one owner?
* RQ3.3 How many edited variants do popular skills have? Families are grouped by normalised skill name (baseline); `reuse.minhash_families` groups by content similarity.""",
SETUP,
"""skills = clean.load_skills()
strict = clean.strict(skills)""",
"""md:## 3.1 Concentration""",
"""conc = pd.DataFrame([{"population": "all", **reuse.concentration(skills["copies"])},
                     {"population": "strict", **reuse.concentration(strict["copies"])}])
save_table(conc, "rq3_concentration")
conc.T""",
"""md:## 3.2 Cross-owner reuse""",
"""dup = strict[strict["copies"] > 1]
print(f"copied skills: {len(dup):,}; spread across >1 owner: {(dup.n_owners > 1).mean():.1%}")
strict.nlargest(15, "copies")[["name", "copies", "n_repos", "n_owners", "location_class", "has_scripts"]]""",
"""md:## 3.3 Variant families""",
"""fam = reuse.name_families(strict)
sizes = fam.groupby("family").agg(variants=("file_sha", "nunique"), occurrences=("copies", "sum"))
print(f"{len(sizes):,} families with >=2 variants, covering {sizes.variants.sum():,} skills")
sizes.sort_values("variants", ascending=False).head(15)""",
],
"04_rq5_security_capabilities.ipynb": [
"""md:# 4. RQ5: Security-sensitive capabilities and their drift across copies

**What we measure.** Not vulnerabilities and not attacks, but *security-sensitive capabilities*: instructions that give the agent the power to cause harm if the skill were malicious, tampered with in a copy, or misused. Each capability maps to the closest CWE weakness class and a severity tier.

**Methodology step 3: quantitative + statistical modelling.**

* RQ5.1 Prevalence of each capability, also weighted by copies (exposure).
* RQ5.2 Drift: within each variant family, which capabilities an edited copy **adds** or **removes** relative to the most-copied member. Additions vs removals are tested with an exact McNemar test.
* RQ5.3 Logistic regression: which variants add capabilities?

**Methodology step 4 (validation)** happens in notebook 05: manual labelling to measure detector precision.""",
SETUP + "\nfrom scipy.stats import binomtest\nfrom statsmodels.stats.proportion import proportion_confint\nimport statsmodels.formula.api as smf",
"""skills = clean.strict(clean.load_skills())
risk_cols = [c for c in skills.columns if c.startswith("risk_")]
pd.DataFrame({"capability": [c[5:] for c in risk_cols],
              "severity": [patterns.RISK_SEVERITY[c[5:]] for c in risk_cols],
              "closest CWE": [patterns.RISK_CWE[c[5:]] for c in risk_cols]})""",
"""md:## 4.1 Prevalence and exposure""",
"""prev = pd.DataFrame({
    "severity": [patterns.RISK_SEVERITY[c[5:]] for c in risk_cols],
    "share_of_skills": skills[risk_cols].mean().values,
    "share_of_occurrences": (skills[risk_cols].mul(skills["copies"], axis=0).sum() / skills["copies"].sum()).values,
}, index=[c[5:] for c in risk_cols]).sort_values(["severity", "share_of_skills"], ascending=[True, False])
save_table(prev.reset_index(names="capability"), "rq5_risk_prevalence")
high = [c for c in risk_cols if patterns.RISK_SEVERITY[c[5:]] == "high"]
print(f"skills with >=1 high-severity capability: {skills[high].any(axis=1).mean():.1%}")
prev""",
"""md:## 4.2 Drift across edited copies""",
"""fam = reuse.name_families(skills)
drift = reuse.variant_drift(fam, risk_cols)
k, n = int(drift["any_added"].sum()), len(drift)
lo, hi = proportion_confint(k, n, method="wilson")
print(f"variants adding >=1 capability: {k:,}/{n:,} = {k/n:.1%} (95% CI {lo:.1%}-{hi:.1%})")
rows = []
for c in risk_cols:
    a, r = int(drift[f"added_{c}"].sum()), int(drift[f"removed_{c}"].sum())
    rows.append({"capability": c[5:], "severity": patterns.RISK_SEVERITY[c[5:]], "added": a, "removed": r,
                 "mcnemar_p": binomtest(a, a + r, 0.5).pvalue if a + r else np.nan})
mc = pd.DataFrame(rows)
save_table(mc, "rq5_mcnemar_added_vs_removed")
mc""",
"""md:## 4.3 Which variants add capabilities? (logistic regression)
Outcome: the variant adds at least one capability absent from its family reference. Predictors: reference popularity (log copies), family size, cross-owner copy, bundled scripts, assistant authorship.""",
"""d = drift.join(skills.set_index("file_sha")[["n_owners", "has_scripts", "first_commit_ai"]], on="file_sha")
d["family_size"] = d.groupby("family")["file_sha"].transform("size") + 1
d = d.assign(added=d["any_added"].astype(int), log_ref_copies=np.log1p(d["ref_copies"]),
             log_family_size=np.log(d["family_size"]), cross_owner=(d["n_owners"] > 1).astype(int),
             has_scripts=d["has_scripts"].fillna(0).astype(int), ai_authored=d["first_commit_ai"].notna().astype(int))
model = smf.logit("added ~ log_ref_copies + log_family_size + cross_owner + has_scripts + ai_authored", data=d).fit(disp=False)
odds = pd.DataFrame({"odds_ratio": np.exp(model.params), "ci_low": np.exp(model.conf_int()[0]),
                     "ci_high": np.exp(model.conf_int()[1]), "p": model.pvalues})
save_table(odds.reset_index(names="term"), "rq5_logit_odds_ratios")
odds.round(3)""",
],
"05_validation_sample.ipynb": [
"""md:# 5. Validation: manual labelling of capability detections

**Methodology steps 3 and 4: qualitative analysis and validation.**

Regular expressions detect a *mention*, not an *instruction to execute*. We draw a stratified random sample (seed 42) of matched snippets per capability and label each by hand:

* `instructs` = the skill tells the agent to perform the action;
* `mentions` = the text refers to it without instructing (for example "never commit the API key");
* `false_match` = the pattern matched something unrelated.

Precision = `instructs` / labelled. The CSV goes to `results/tables/validation_sample.csv`; fill the `label` column by hand and re-run the last cell.""",
SETUP + "\nimport re",
"""PER_CATEGORY = 12   # 9 categories x 12 = 108 snippets
skills = clean.strict(clean.load_skills())
rows = []
for cap, rx in patterns.COMPILED_RISKS.items():
    hits = skills[skills[f"risk_{cap}"].fillna(False)]
    pick = hits.sample(min(PER_CATEGORY, len(hits)), random_state=42)
    texts = db.query(f"SELECT file_sha, content FROM artifacts WHERE dedup_primary = 1 AND file_sha IN ({','.join('?' * len(pick))})",
                     tuple(pick["file_sha"]))
    for _, t in texts.iterrows():
        m = rx.search(t["content"] or "")
        if m:
            s = max(0, m.start() - 160); e = min(len(t["content"]), m.end() + 160)
            rows.append({"capability": cap, "file_sha": t["file_sha"], "snippet": t["content"][s:e].replace("\\n", " "), "label": ""})
sample = pd.DataFrame(rows)
out = ROOT / "results/tables/validation_sample.csv"
if not out.exists():
    sample.to_csv(out, index=False)
print(f"{len(sample)} snippets -> {out}")
sample.head()""",
"""md:## Precision per capability (after labelling)""",
"""lab = pd.read_csv(ROOT / "results/tables/validation_sample.csv").fillna({"label": ""})
done = lab[lab["label"] != ""]
if done.empty:
    print("No labels yet: fill the 'label' column in validation_sample.csv")
else:
    prec = done.groupby("capability")["label"].apply(lambda s: (s == "instructs").mean()).rename("precision")
    save_table(prec.reset_index(), "validation_precision")
    display(prec.to_frame())""",
],
}

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, cells in NOTEBOOKS.items():
        nbf.write(nb(cells), OUT / name)
        print("wrote", OUT / name)
