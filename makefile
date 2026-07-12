# Makefile -- shortcuts for the kelp-forest simulation.
# Run `make` or `make help` to list targets.

PY := python3
SHELL := /bin/bash
.ONESHELL:

.DEFAULT_GOAL := help

# ---------------------------------------------------------------- basics
.PHONY: help install test run sweep clean

help:  ## show this help
	@echo "Kelp-forest simulation -- available targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) \
		| sed -E 's/:.*## /\t/' | sort | awk -F '\t' '{printf "  %-16s %s\n", $$1, $$2}'

install:  ## install optional analysis/plot/test dependencies
	$(PY) -m pip install -r requirements.txt

test:  ## run the pytest suite
	$(PY) -m pytest -q

run:  ## baseline interactive run (run.py)
	$(PY) run.py

sweep:  ## tipping-point otter-mortality sweep
	$(PY) run.py --sweep

.PHONY: run_experiment
run_experiment:  ## interactively build & run a custom experiment (blank = skip)
	@read -rp "Run ID (e.g. 013): " id
	read -rp "Purpose: " purpose
	read -rp "seed (leave blank for default): " seed
	read -rp "otter_mortality (leave blank for default): " om
	read -rp "steps (leave blank for default): " steps
	read -rp "kelp_growth (leave blank for default): " kg
	read -rp "storm_rate (leave blank for default): " sr
	read -rp "disease_rate (leave blank for default): " dr
	read -rp "n_urchins0 (leave blank for default): " nu
	read -rp "width (leave blank for default): " w
	read -rp "height (leave blank for default): " h
	read -rp "extra --set flags (blank=none): " extra
	if [ -z "$$id" ]; then echo "error: a Run ID is required."; exit 1; fi
	if [ -z "$$purpose" ]; then purpose="Custom run $$id"; fi
	args=""
	[ -n "$$seed" ]  && args="$$args --set seed=$$seed"
	[ -n "$$om" ]    && args="$$args --set otter_mortality=$$om"
	[ -n "$$steps" ] && args="$$args --set steps=$$steps"
	[ -n "$$kg" ]    && args="$$args --set kelp_growth=$$kg"
	[ -n "$$sr" ]    && args="$$args --set storm_rate=$$sr"
	[ -n "$$dr" ]    && args="$$args --set disease_rate=$$dr"
	[ -n "$$nu" ]    && args="$$args --set n_urchins0=$$nu"
	[ -n "$$w" ]     && args="$$args --set width=$$w"
	[ -n "$$h" ]     && args="$$args --set height=$$h"
	[ -n "$$extra" ] && args="$$args $$extra"
	echo "+ $(PY) run_experiment.py --id $$id --purpose \"$$purpose\"$$args"
	$(PY) run_experiment.py --id "$$id" --purpose "$$purpose" $$args

clean:  ## remove generated data and caches
	rm -f results/run_*.csv results/run_*.json results/manifest.csv
	rm -rf .pytest_cache **/__pycache__ __pycache__

