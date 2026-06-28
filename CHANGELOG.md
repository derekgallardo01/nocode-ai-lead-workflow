# Changelog

Notable changes to the no-code AI lead workflow. Dates are when the change
landed on `main`.

## 2026-06-27 — Docker support
- Dockerfile so the workflow runs via `docker run` without a Python install
- README "Run in Docker" section

## 2026-06-27 — Second leads dataset (real-estate brokerage)
- `data/leads-real-estate.json` — 8 sample leads (1 dedupe pair across
  email + CRM, 1 fallback-confidence vague message) in a real-estate context
- `evals/golden.json` gains a real-estate end-to-end case
- CI smoke-tests both default and real-estate datasets

## 2026-06-27 — GitHub Actions CI
- `.github/workflows/ci.yml` running pytest + eval + smoke-test on Python 3.11
- CI status badge added to README

## 2026-06-27 — Build-out: dedupe + human-review queue
- `dedupe()` collapses leads sharing a normalized email; records merged pairs
  for audit
- `_classify` returns `(category, confidence, matched_keywords)` where
  confidence is `strong / weak / fallback`
- `Processed` grows `confidence`, `needs_human_review`, `matched_keywords`,
  `merged_from` fields
- `human_review_queue()` and `follow_ups()` are disjoint — fallback-confidence
  leads bypass auto-reply
- `run()` returns a counts dict and writes `for_human_review.json` alongside
  `follow_ups.json` and `crm.csv` / `crm.json`
- `cli.py` argparse with `--out / --no-dedupe / --no-human-review`
- `data/leads.json` extended to 9 leads (3 dedupe candidates, 1 fallback)
- `evals/golden.json` (11 cases) + CI-gating runner
- 11 new tests covering dedupe variants, fallback flagging, no-dedupe and
  no-human-review modes
- `docs/architecture.md`, `customization.md`, `evaluation.md`
- `docs/sample-run.txt` (default run + CRM + human-review + follow-ups
  snippets)
- README expanded with architecture, sample, eval, customization sections

## 2026-06-27 — Initial public release
- Lead pipeline: classify → summarize → draft reply → save to CRM →
  queue follow-up; spam suppressed
- Buildable in Make.com / Zapier / n8n / Power Automate via
  `blueprint.md`
- 5 unit tests
