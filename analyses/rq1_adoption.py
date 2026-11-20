# %% [markdown]
# # RQ1 — Adoption and authorship
# * RQ1.1 How fast does the format spread after Oct 2025, and who adopts it first
#   (language, stars, repository age)?
# * RQ1.2 How many skills are created by agents themselves (AI co-author trailers,
#   bot accounts), and how does this share evolve per monthly cohort?
# Caveat: dates exist only for the history sample (all standard locations +
# size-stratified `other`), see `adoption.history_coverage`.

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src") if "__file__" in dir() else "../src")
import matplotlib.pyplot as plt

from gitskills import adoption, clean
from gitskills.plots import save, save_table

skills = clean.strict(clean.load_skills())
occ = clean.load_occurrences()
save_table(adoption.history_coverage(skills), "rq1_history_coverage")

# %% New skills per month, only where history coverage is (near) complete.
# On the sample this is `canonical` only (~100%); `skills-dir` and `other` are ~11%.
cov = adoption.history_coverage(skills)
complete = cov.loc[cov["share"] >= 0.9, "location_class"].tolist()
print(f"location classes with complete history: {complete}")
std = skills[skills["location_class"].isin(complete)]
cohorts = adoption.monthly_cohorts(std, by="location_class")
pivot = cohorts.pivot(index="first_month", columns="location_class", values="new_skills").fillna(0)
fig, ax = plt.subplots()
pivot.plot(ax=ax, marker=".")
ax.set_ylabel("new distinct skills")
save(fig, "rq1_monthly_new_skills")
save_table(cohorts, "rq1_monthly_cohorts")

# %% Adopter profile: stars, language, age of repository at adoption
prof = adoption.adopter_profile(occ)
save_table(prof.describe(include="all").T.reset_index(), "rq1_adopter_profile", latex=False)

# %% Machine authorship per cohort
h = skills[skills["has_history"]].copy()
h["ai_first"] = h["first_commit_ai"].notna() | h["first_commit_bot"]
ai = h.groupby("first_month")["ai_first"].agg(["size", "mean"]).reset_index()
save_table(ai, "rq1_ai_authorship_by_month")
save_table(h["first_commit_ai"].value_counts().rename("skills").reset_index(), "rq1_ai_assistants")
