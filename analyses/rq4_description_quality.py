# %% [markdown]
# # RQ4 — Software metrics for natural-language instructions
# * RQ4.1 Distributions of size, structure and directive density of skills.
# * RQ4.2 Which description properties (length, explicit trigger phrase,
#   spec compliance) are associated with reuse (copies, cross-owner spread)
#   and maintenance (commit count)?
# The description is what the agent matches against the task, so it is the
# "interface" of a skill.

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src") if "__file__" in dir() else "../src")
import numpy as np
import pandas as pd
from scipy import stats

from gitskills import clean
from gitskills.plots import save_table

skills = clean.strict(clean.load_skills())

# %% Metric distributions
metrics = ["body_words", "n_headings", "n_code_blocks", "n_list_items", "directives_per_100w",
           "desc_words", "sibling_count", "commit_count"]
save_table(skills[metrics].describe(percentiles=[.25, .5, .75, .9]).T.reset_index(), "rq4_metric_distributions")

# %% Description properties vs reuse (Mann-Whitney + Cliff's delta)
def cliffs_delta(a, b):
    a, b = np.asarray(a), np.asarray(b)
    u = stats.mannwhitneyu(a, b).statistic
    return 2 * u / (len(a) * len(b)) - 1

rows = []
for prop in ["desc_has_trigger", "desc_spec_ok", "name_spec_ok", "has_scripts", "has_references"]:
    g = skills[prop].fillna(0).astype(bool)
    for outcome in ["copies", "n_owners", "commit_count"]:
        a, b = skills.loc[g, outcome].dropna(), skills.loc[~g, outcome].dropna()
        if len(a) > 10 and len(b) > 10:
            p = stats.mannwhitneyu(a, b).pvalue
            rows.append({"property": prop, "outcome": outcome, "n_true": len(a), "n_false": len(b),
                         "median_true": a.median(), "median_false": b.median(),
                         "cliffs_delta": cliffs_delta(a, b), "p": p})
save_table(pd.DataFrame(rows), "rq4_description_vs_reuse")

# %% Rank correlation of description length with copies
rho = stats.spearmanr(skills["desc_words"], skills["copies"], nan_policy="omit")
print(f"Spearman desc_words vs copies: rho={rho.statistic:.3f} p={rho.pvalue:.2g}")
