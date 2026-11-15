# %% [markdown]
# # RQ3 — Reuse without a package manager
# * RQ3.1 How concentrated is reuse (long tail vs a few mass-copied templates)?
# * RQ3.2 Does copying cross owners (ecosystem reuse) or stay within an owner
#   (internal duplication / catalogs)?
# * RQ3.3 Near-duplicate families: how many variants do popular skills have,
#   and how far do variants drift from the most-copied member?

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src") if "__file__" in dir() else "../src")
import pandas as pd

from gitskills import clean, reuse
from gitskills.plots import save_table

skills = clean.load_skills()  # reuse is measured on every content, then on strict
strict = clean.strict(skills)

# %% Concentration
conc = pd.DataFrame([
    {"population": "all", **reuse.concentration(skills["copies"])},
    {"population": "strict", **reuse.concentration(strict["copies"])},
])
save_table(conc, "rq3_concentration")

# %% Cross-owner reuse
dup = strict[strict["copies"] > 1].copy()
dup["cross_owner"] = dup["n_owners"] > 1
save_table(dup["cross_owner"].value_counts(normalize=True).rename("share").reset_index(), "rq3_cross_owner")
top = strict.nlargest(25, "copies")[["name", "copies", "n_repos", "n_owners", "location_class", "has_scripts"]]
save_table(top, "rq3_top_copied", latex=False)

# %% Name-based families (baseline; replace with reuse.minhash_families on content)
fam = reuse.name_families(strict)
fam_sizes = fam.groupby("family").agg(variants=("file_sha", "nunique"), occurrences=("copies", "sum"))
save_table(fam_sizes.sort_values("variants", ascending=False).head(25).reset_index(), "rq3_name_families")
