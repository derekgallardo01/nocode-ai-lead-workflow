# Evaluation

The eval set tests the workflow end-to-end on small, deterministic inputs.
Each case is either an inline list of leads OR a path to a leads JSON file,
with expected counts and category distributions. It's the thing that gates
"did this rule change break something" — exit code 0 if everything matches,
1 if anything doesn't.

## What it does

[evals/run.py](../evals/run.py) loads [evals/golden.json](../evals/golden.json),
runs each case through `dedupe` + `process_leads` (or `run` for end-to-end
cases), and checks: deduped count, merged-pair count, follow-up count,
human-review count, and category distribution.

```text
Eval: 11/11 passed (100%)
```

On failure you get the specific mismatch:

```text
Eval: 10/11 passed (91%)

1 failed:
  [fallback-flagged]
       human_review=0 expected=1
       follow_ups=1 expected=0
```

## Case format

Two shapes — inline:

```json
{
  "id": "quote-strong",
  "leads": [{"id": "q1", "channel": "email", "name": "A", "email": "a@x.co",
             "message": "Send us a quote for 50 seats and book a demo please."}],
  "expect": {"deduped": 1, "categories": {"quote_request": 1},
             "follow_ups": 1, "human_review": 0}
}
```

…and file-backed:

```json
{
  "id": "sample-end-to-end",
  "leads_path": "data/leads.json",
  "expect": {"raw_leads": 9, "deduped": 7, "merged_pairs": 2,
             "follow_ups": 5, "human_review": 1}
}
```

| Expect field | Meaning |
|--------------|---------|
| `raw_leads` | Input row count before dedupe. |
| `deduped` | Distinct leads after `dedupe`. |
| `merged_pairs` | Number of pairs collapsed by `dedupe`. |
| `categories` | Per-category count across all processed leads. |
| `follow_ups` | Drafts that would be sent (non-spam + non-human-review). |
| `human_review` | Leads routed to the human-review queue. |

## Adding cases

Three patterns:

**1. Capture every misrouted lead as a regression case.** When a real client
shows you a lead the workflow categorised wrong (or auto-replied to when it
shouldn't have), copy it into `golden.json` with the *correct* expected
category/flag *before* changing any rules. That way the fix doesn't quietly
break a different case.

**2. Add paraphrases.** "Send us a quote", "Pricing for our team", "What
does this cost?" — three different surface forms of the same intent. All
should route to `quote_request`. Same for `support_request` paraphrases
("can't log in", "page won't load", etc.).

**3. Add adversarial cases.** A legitimate user mentioning "crypto" once
("we're a crypto exchange and need…") shouldn't be spam-classified. A user
who says "thanks for the partnership" in passing shouldn't be routed to the
partnership category. Add these and tune `RULES` until both old and new
cases pass.

## Workflow when tuning

1. Add the failing case(s) to `golden.json`.
2. Run `python evals/run.py` and see them fail.
3. Edit `RULES`, `_classify` confidence rules, or `dedupe` normalization.
4. Re-run. Iterate until 100% pass and existing cases didn't regress.

The end-to-end case (`sample-end-to-end`) is the canary: if you change a
default rule, it'll catch the change because the counts shift.

## What an eval set is not

- **Not a replacement for reading the human-review queue.** Tests can prove a
  lead *got* flagged; only a human can decide if it *should* have been.
- **Not a check on reply quality.** Drafts are template strings here; for a
  real model, add an LLM-output eval that scores replies against a rubric.
- **Not exhaustive.** 11 cases here are illustrative. A serious deployment
  runs with 50–100 cases across every channel, every category, and the long
  tail of weird-but-real messages.
