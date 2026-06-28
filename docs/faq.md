# FAQ

## Why dedupe before classify?

Classifying first means doing twice the LLM work AND having to reconcile
potentially-different categories for the same person (e.g. their form
submission was classified as "quote", their follow-up email as
"support"). Dedupe-first is one record per person, one classification,
one audit trail — and the audit trail (`merged_from`) survives, so you
can still see that Dana submitted through both channels.

## What's the difference between "weak" and "fallback" confidence?

- **Strong**: 2+ keyword matches in one category → confident
  classification → auto-reply.
- **Weak**: exactly 1 keyword matched → still a defensible category →
  auto-reply (single keyword like "refund" or "demo" is enough on its
  own).
- **Fallback**: zero keywords matched → default category was used →
  flagged for human review. This is genuinely unknown intent, not a
  weak signal.

The split matters: a 1-keyword match in a normal category is fine. A
0-keyword match means we have no idea, and shouldn't be auto-replying.

## Why don't spam leads go to human review?

Spam is its own exit — logged in CRM but no follow-up drafted AND no
human-review queue entry. Humans don't need to triage SEO outreach;
the system just suppresses it. If you want to also flag low-confidence
spam matches (in case a legitimate user mentioned "crypto" in passing),
the current implementation does: `needs_review = fallback OR (spam AND
weak)`.

## How do I add a new category?

Append to `RULES` in `pipeline.py` with keywords, and add a `REPLY_
TEMPLATES` entry. Order matters — first matching category wins. Put
specific categories before broader ones.

## Why isn't this just one of the no-code tools (Make / Zapier)?

The kit IS designed to be built in Make / Zapier / n8n / Power Automate
— see [`blueprint.md`](../blueprint.md) at the repo root for the
node-by-node mapping. The Python here is the **executable spec**: it
proves the logic works, it's testable in `pytest`, and the eval set
gates the regression net. The no-code build is downstream.

## How does dedupe handle the "+aliases" email case?

The default `_norm_email()` only lowercases and trims. To handle
`dana+work@acme.co` = `dana@acme.co`, override with a parser that
strips `+...` from the local part — example in
[customization.md §5](customization.md#5-dedupe-strategy).

## What happens if I run the pipeline twice on the same leads?

The CRM (`crm.csv` / `crm.json`) is overwritten each run — it's a
snapshot, not append-only. For a production setup, swap `save_crm` for
something that writes to a real CRM via API and dedups on lead id.

## How do I send the human-review queue to Slack / Teams?

`human_review_queue()` currently returns a list of dicts. Replace its
body with a `requests.post(...)` to your Slack webhook OR add a Power
Automate flow that polls `for_human_review.json` in a SharePoint
library. The kit doesn't include the integration because it'd add a
network dep and the routing destination is highly per-client.
