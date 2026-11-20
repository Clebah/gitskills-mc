# %% [markdown]
# # RQ2 — A shared format or a Claude Code format?
# * RQ2.1 What share of skills live in vendor-neutral (`skills/`) vs
#   tool-specific (`.claude/skills/`) locations, and how does it change per month?
# * RQ2.2 Do skill texts address one named tool or any agent?
# * RQ2.3 How closely do skills follow the specification (name/description
#   limits, front-matter keys), and do non-standard keys converge?

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src") if "__file__" in dir() else "../src")
import pandas as pd

from gitskills import adoption, clean
from gitskills.plots import save_table

skills = clean.strict(clean.load_skills())

# %% Location share per monthly cohort
loc = adoption.monthly_cohorts(skills, by="location_class")
save_table(loc, "rq2_location_share_by_month")

# %% Tools named in the text
tools = skills["tools_named"].fillna("").str.split(",").explode()
tools = tools[tools != ""].value_counts().rename("skills").reset_index()
save_table(tools, "rq2_tools_named")
save_table(skills["n_tools_named"].value_counts().sort_index().rename("skills").reset_index(),
           "rq2_n_tools_named")

# %% Specification compliance
spec = skills[["name_spec_ok", "desc_spec_ok", "has_allowed_tools"]].mean().rename("share").reset_index()
save_table(spec, "rq2_spec_compliance")
keys = skills["fm_keys"].fillna("").str.split(",").explode()
save_table(keys[keys != ""].value_counts().head(30).rename("skills").reset_index(), "rq2_frontmatter_keys")
