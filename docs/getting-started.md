# Getting started

A 5-minute walkthrough — no LLM keys, no CRM, no third-party automation
tool.

## 1. Clone and run the demo

```bash
git clone https://github.com/derekgallardo01/nocode-ai-lead-workflow.git
cd nocode-ai-lead-workflow
python run.py
```

You should see 9 raw leads → 7 deduped (2 merged pairs) → 5 follow-ups
drafted + 1 routed to the human-review queue. Outputs land in `out/`:

- `crm.csv` / `crm.json` — every processed lead
- `follow_ups.json` — ready-to-send drafts
- `for_human_review.json` — leads flagged for human triage

## 2. Run the eval set

```bash
python evals/run.py
```

`Eval: 12/12 passed (100%)`. Cases cover each category, dedupe positive
/ negative, spam suppression, fallback flagging, end-to-end (default
leads), end-to-end (real-estate leads).

## 3. Try the CLI

```bash
python cli.py data/leads.json                   # default
python cli.py data/leads-real-estate.json       # second worked dataset
python cli.py data/leads.json --no-dedupe       # see what the dedupe is doing
python cli.py data/leads.json --no-human-review # route everything to follow-ups
```

## 4. See the live demo

The CI deploys the pipeline output as static HTML on every push:

- https://derekgallardo01.github.io/nocode-ai-lead-workflow/

Both datasets processed end-to-end (KPI cards, dedupe summary, per-
category breakdown, processed-leads table, human-review queue).

## 5. Run in Docker (optional)

```bash
docker build -t nocode-lead-workflow .
docker run --rm nocode-lead-workflow
```

## What to read next

- [Architecture](architecture.md) · [Customization](customization.md) ·
  [Evaluation](evaluation.md) · [Diagrams](diagrams.md) · [FAQ](faq.md)

## Building it for real

The Python pipeline proves the **logic**. The
[blueprint.md](../blueprint.md) at the repo root maps each step to
the equivalent node in Make.com, Zapier, n8n, and Power Automate. The
default classifier/answerer is a deterministic stub; swap for a real
LLM via the `LLM_PROVIDER` env var seam.
