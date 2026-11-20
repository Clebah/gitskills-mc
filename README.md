# gitskills-mc

Analysis pipeline for the **GitSkills** dataset, built for the
[MSR 2027 Mining Challenge](https://2027.msrconf.org/track/msr-2027-mining-challenge).

GitSkills (Destefanis, Graziotin, Vaccargiu, Ortu; arXiv 2608.10906) contains
3,797,117 `SKILL.md` files from 282,200 public GitHub repositories, collected
in July 2026 and grouped into 1,877,981 distinct contents. It ships as a
single SQLite file (~41 GB) with four tables: `artifacts`, `repos`,
`artifact_siblings`, and `mining_runs`.

## Deadlines (AoE)

| Milestone | Date |
|---|---|
| Abstract (HotCRP) | **2026-12-18** |
| Paper (4 pages + 1 for references, IEEEtran `10pt,conference`, double-anonymous, ethics section required) | **2026-12-23** |
| Notification | 2027-01-19 |
| Camera-ready | 2027-01-26 |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
make install          # package + extras (nlp, hf, notebooks, dev)
make sample           # official sample: 13k skills, 277 MB (same schema as the full dataset)
make features         # cleaning + features -> data/processed/*.parquet
make analyses         # EDA + RQ scripts -> results/tables, results/figures
make notebooks        # generate and execute the Jupyter notebooks
make test
```

For the full dataset, run `make full` (Zenodo, ~41 GB) or `make parquet`
(Parquet mirror on Hugging Face), then
`make features DB=data/raw/<file>.db`. Every query written against the
sample runs unchanged on the full dataset.

## Layout

```
src/gitskills/
  config.py      paths, URLs, specification limits, snapshot id
  db.py          read-only SQLite access (query / chunked iter_query)
  clean.py       populations and filters ("strict" population) + filter report
  features.py    per-skill features: front matter, spec compliance, body
                 structure, tools named, risky capabilities, AI co-authorship
                 in commits, natural language (optional)
  patterns.py    versioned regex vocabularies (tools, triggers, risks)
  reuse.py       reuse concentration (Gini, top-k), variant families
                 (by name or MinHash), and variant drift
  adoption.py    monthly cohorts, history coverage, adopter profile
  plots.py       IEEE-column figure style and table export (.csv/.tex)
scripts/
  download.py         sample (GitHub) | full dataset (Zenodo) | Parquet (HF)
  build_features.py   writes data/processed/skills.parquet and occurrences.parquet
notebooks/            the narrated analysis, one notebook per methodology step:
  01_data_and_cleaning  02_rq1_adoption_and_authorship  03_rq3_reuse
  04_rq5_security_capabilities  05_validation_sample
analyses/             the same analyses as plain scripts (batch runs)
  00_eda.py  rq1_adoption.py  rq2_shared_format.py  rq3_reuse.py
  rq4_description_quality.py  rq5_security.py
tests/                synthetic database with the real schema + feature and pipeline tests
```

## Data caveats (handled in `clean.py`)

- **Two units of analysis.** Occurrence (a row of `artifacts`) for adoption
  and reuse; distinct skill (`dedup_primary = 1`, the only rows with
  `content`) for text, structure, and security.
- **"Strict" population.** The dataset includes lowercase `skill.md` files,
  invalid front matter, and files that predate the format (Oct 2025).
  `clean.strict` removes them; `population_report` shows how many each filter
  drops. On the sample: 13,000 → 11,195 skills (86%).
- **History is sampled.** On the sample, `first_commit_at` covers ~100% of
  `canonical` skills (`.claude/skills/`) but only ~11% of `skills-dir` and
  `other`. Time series must use only fully covered classes or reweight the
  stratum.
- **Representative ≠ original.** The enriched copy is chosen by a
  deterministic rule; folder contents and history describe that repository only.
- **Current path.** For renamed files, `first_commit_at` dates the rename.
- **Lower bound.** Code search indexes only default branches, files under
  384 KB, and forks with more stars than their parent.

## Candidate research questions

Each RQ has a script in `analyses/`. The figures below come from the
**sample** (13k skills) and only show whether a question is promising; the
paper needs numbers from the full dataset.

**RQ1 — Adoption and agent authorship.** How fast did the format spread after
Oct 2025, who adopts it first (language, stars, repository age), and how many
skills do agents write themselves?
*Sample signal:* ~30% of skills with history have an AI assistant
`Co-authored-by` trailer on their first commit (almost all Claude).

**RQ2 — A shared format or a Claude Code format?** What share lives in
vendor-neutral (`skills/`) vs tool-specific (`.claude/skills/`) locations, how
many skills name a specific tool, and how closely do they follow the
specification?
*Signal:* 94% of `name` and 98% of `description` fields meet the spec limits;
Claude is named in ~2.5k skills, Codex in ~770, Cursor in ~510.

**RQ3 — Reuse without a package manager.** How concentrated is reuse, and does
it cross owners? How many variants (edited copies) do popular skills have?
*Signal:* 74% of contents are unique, yet 1% of contents account for 23% of
occurrences (Gini 0.53); 76% of duplicated contents appear under more than
one owner.

**RQ4 — Metrics for natural-language instructions.** Which software metrics
(size, churn, clones, readability) have skill equivalents? Does the
description (what the agent matches against the task) predict reuse and
maintenance?
*Signal:* small effects; descriptions that violate the spec are copied less
(Cliff's δ ≈ 0.1).

**RQ5 — Trust and supply chain.** How often do skills tell the agent to fetch
remote code, install packages, touch secrets, or skip confirmations? Do
variants of popular skills *add* such capabilities relative to the family's
most-copied member?
*Signal:* 8% of skills fetch remote content and 11% install packages; ~21% of
variants add at least one risk category absent from the most-copied version
(name-based heuristic; needs validation).

### Paper plan

A 4-page paper fits about three well-executed RQs. The plan is
**RQ1 + RQ3 + RQ5**:

- **RQ1 (adoption and agent authorship)** sets the context: how big and how
  fast the ecosystem is, and who writes skills. Keep it descriptive and short
  so it leaves room for the other two.
- **RQ3 (reuse)** uses the dataset's distinctive feature, that every copy is
  preserved, to show how skills spread without a registry.
- **RQ5 (security drift)** is the main contribution: whether edited copies of
  popular skills add risky capabilities. It is the analog of a supply-chain
  attack in an ecosystem without a registry, which the dataset authors list
  as open.

RQ2 and RQ4 are mostly descriptive or show small effects on the sample, so
they are kept as secondary material.

## Next steps

1. Run the pipeline on the full dataset (`make full`, then `make features`;
   extraction is parallel and takes ~20 s per 13k skills on 4 cores).
2. Replace name-based families with `reuse.minhash_families` over content.
3. Validate the regexes in `patterns.py` on a manually labelled sample
   (report precision) before using the numbers in the paper.
4. Purpose taxonomy (RQ1b in the dataset paper): cluster description
   embeddings + manual labelling.
5. Anonymous replication package (anonymous.4open.science / Zenodo) and cite
   the snapshot `GitSkills July 2026 (10.5281/zenodo.21875637)`.

## Dataset citation

G. Destefanis, D. Graziotin, M. Vaccargiu, and M. Ortu, "GitSkills: A Dataset
of Agent Skills on GitHub," in *Proc. MSR '27*, 2027. arXiv:2608.10906.
