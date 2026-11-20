# %% [markdown]
# # 00 — Exploratory data analysis
# Descriptive statistics of the snapshot: table sizes, population filters,
# location classes, languages, copies and body length. Run after `make features`.
# Works as a script or as a notebook (`jupytext --to notebook analyses/00_eda.py`).

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src") if "__file__" in dir() else "../src")
import matplotlib.pyplot as plt
import numpy as np

from gitskills import clean, db
from gitskills.plots import save, save_table

skills = clean.load_skills()
occ = clean.load_occurrences()

# %% Table sizes and population filters
save_table(db.table_counts(), "eda_table_counts")
save_table(clean.population_report(skills), "eda_population_filters")

# %% Location class and filename variants (occurrence level)
loc = occ["location_class"].value_counts(normalize=True).rename("share").reset_index()
save_table(loc, "eda_location_class")
save_table(occ["filename"].value_counts().rename("files").reset_index(), "eda_filename_variants")

# %% Repository languages (repository level)
repos = occ.drop_duplicates("repo_full_name")
save_table(repos["language"].value_counts().head(15).rename("repos").reset_index(), "eda_languages")

# %% Copies per distinct content (log-log)
fig, ax = plt.subplots()
vc = skills["copies"].value_counts().sort_index()
ax.loglog(vc.index, vc.values, ".", ms=3)
ax.set_xlabel("copies of a distinct content")
ax.set_ylabel("# distinct contents")
save(fig, "eda_copies_loglog")

# %% Body length
fig, ax = plt.subplots()
b = skills["body_chars"].dropna()
ax.hist(np.log10(b[b > 0]), bins=50)
ax.set_xlabel("log10(body characters)")
ax.set_ylabel("# skills")
save(fig, "eda_body_length")

# %% Composition: scripts and references
comp = skills[skills["composition_fetched"].eq(1)][["has_scripts", "has_references"]].mean()
print(comp)
