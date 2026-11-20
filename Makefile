PY ?= python
DB ?= data/raw/agent_skills_sample.db

.PHONY: install sample full parquet clean-data features eda analyses notebooks test

install:            ## install package + extras in the current env
	$(PY) -m pip install -e ".[dev,nlp,hf,notebooks]"

sample:             ## download the official 13k-skill sample (~280 MB unpacked)
	$(PY) scripts/download.py sample

full:               ## download the full SQLite dataset from Zenodo (~41-44 GB)
	$(PY) scripts/download.py zenodo

parquet:            ## download the Parquet mirror from Hugging Face
	$(PY) scripts/download.py hf

features:           ## clean + derive per-skill features into data/processed/
	GITSKILLS_DB=$(DB) $(PY) scripts/build_features.py

eda:                ## descriptive statistics and figures
	GITSKILLS_DB=$(DB) $(PY) analyses/00_eda.py

analyses: features eda  ## run every RQ script
	for f in analyses/rq*.py; do GITSKILLS_DB=$(DB) $(PY) $$f || exit 1; done

test:
	$(PY) -m pytest -q

notebooks:          ## regenerate and execute the Jupyter notebooks (needs `make features`)
	$(PY) scripts/build_notebooks.py
	cd notebooks && GITSKILLS_DB=$(abspath $(DB)) $(PY) -m jupyter nbconvert --to notebook --execute --inplace *.ipynb
