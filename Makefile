PY ?= python

.PHONY: help install test eval eval-stub eval-score fixtures-green corpus lint

help:
	@echo "make install      install python deps (anthropic, pytest)"
	@echo "make test         unit tests (no model, no network)"
	@echo "make eval         full run: agent over the corpus + metrics + sweep"
	@echo "make eval-stub    same pipeline with the keyword stub: no key, no spend"
	@echo "make eval-score   re-score stored predictions without calling a model"
	@echo "make corpus       regenerate the synthetic half of the corpus"
	@echo "make fixtures-green  prove the fixture suite passes unmutated"

install:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest tests/ -q

# The published numbers. Needs ANTHROPIC_API_KEY for --backend api; use
# --backend cli to run it through the Claude Code CLI without a key.
eval:
	$(PY) eval/run_eval.py --backend api --modell claude-sonnet-5

eval-stub:
	$(PY) eval/run_eval.py --backend stub --ausgabe eval/ergebnis_stub.json

eval-score:
	$(PY) eval/run_eval.py --nur-auswerten

corpus:
	cd fixtures && node generate.mjs

fixtures-green:
	cd fixtures && npx playwright test

readme:
	$(PY) eval/readme_zahlen.py

korpus-pruefen:
	$(PY) eval/pruefe_korpus.py

fehler:
	$(PY) eval/fehleranalyse.py
