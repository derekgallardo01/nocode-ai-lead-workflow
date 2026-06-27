# Customization

Six things you'll typically tune per client.

## 1. Edit the RULES table

The classification rules live at the top of [pipeline.py](../pipeline.py):

```python
RULES = [
    ("quote_request", ["quote", "pricing", "price", "cost", "estimate", "buy", "demo", "seats", "enterprise plan"]),
    ("billing", ["invoice", "refund", "payment", "charge", "billing", "receipt", "charged"]),
    ("support_request", ["help", "issue", "broken", "error", "not working", "support", "bug", "asap"]),
    ("partnership", ["partner", "reseller", "collaborat", "affiliate", "white-label"]),
    ("spam_or_irrelevant", ["seo services", "rank your", "crypto", "loan offer", "cheap seo"]),
]
```

- **Order matters** — the first matching category wins. Put more specific
  categories before broader ones.
- **Substrings, not whole words** — "collaborat" matches both "collaborate"
  and "collaboration". Use the shortest stable stem.
- **Phrases work** — multi-word keywords like "enterprise plan" or "cheap seo"
  match as exact substrings (no tokenization), which is robust to punctuation
  but case-sensitive to spaces.

Always add an eval case to [evals/golden.json](../evals/golden.json) for any
keyword you add — that's the regression net for "did this fix break
something else?"

## 2. Tighten "confident enough" for auto-reply

Default: human review fires only on `confidence == "fallback"`. To also
demand multiple keywords (no weak auto-replies):

```python
needs_review = (
    conf in ("fallback", "weak")
    or (cat == "spam_or_irrelevant" and conf == "weak")
)
```

The tradeoff: human-review queue gets longer; auto-reply throughput drops.
Tune per client based on how much their team can triage.

## 3. Swap the stub for a real LLM

The seam is `complete(lead)` in [pipeline.py](../pipeline.py). The default
path calls `_classify` + `_summarize` + `REPLY_TEMPLATES[cat]`; a real model
gets the same `Lead` and should return `(summary, category, draft_reply)`.

Suggested prompt (JSON-out for parseability):

```text
You are an inbound-lead triage assistant. Reply ONLY with strict JSON of the
shape {"summary", "category", "draft_reply"}.

categories: ["quote_request","support_request","partnership","billing","spam_or_irrelevant"]
- Use "spam_or_irrelevant" for SEO/crypto outreach.
- Be terse (<=200 chars summary).
- draft_reply is empty when category is spam_or_irrelevant.

Lead from {channel}: "{message}"
```

Wire it in `_real_complete` (currently raises) — call your provider via
`urllib.request` to stay dependency-free, then `json.loads` the response.

## 4. Reply templates

Edit `REPLY_TEMPLATES` in [pipeline.py](../pipeline.py). Each value is the
body of the draft (without the `Hi {name},\n\n…\n\nBest,\nThe Team` wrapper
— that's added by `follow_ups`). A `""` template means no reply is drafted
(used for spam).

For per-channel templates, change `follow_ups` to look up
`REPLY_TEMPLATES_BY_CHANNEL[p.channel][p.category]` and fall through to the
flat `REPLY_TEMPLATES`.

## 5. Dedupe strategy

Default: `_norm_email(email) = email.lower().strip()` — exact, case-
insensitive email match. To handle "+aliases" (`dana+work@acme.co` =
`dana@acme.co`):

```python
def _norm_email(email):
    local, _, domain = email.lower().strip().partition("@")
    local = local.split("+", 1)[0]
    return f"{local}@{domain}"
```

For fuzzy match on name + message body (when email isn't reliable):

```python
def _key(lead):
    return (
        lead.name.lower(),
        tuple(sorted(set(re.findall(r"\w+", lead.message.lower())))[:8])
    )
```

Then group leads with `groupby` instead of an email-keyed dict. **Add a
dedupe eval case before changing this** — it's the function with the highest
risk of false-merges.

## 6. Route the human-review queue

Default: `for_human_review.json` next to the other output files. To route to
Slack / Teams / a CRM task, change `human_review_queue` so each entry posts
to your destination instead of (or in addition to) being written to disk:

```python
def human_review_queue(processed):
    queue = []
    for p in processed:
        if not p.needs_human_review:
            continue
        entry = {…}
        queue.append(entry)
        post_to_slack(entry)  # or create_jira_ticket(entry)
    return queue
```

Keep the file write too — it's the audit log, not just a transport.

## Validating any change

```bash
python -m pytest -q
python evals/run.py
python run.py
```

If you changed `RULES`, `_classify`, or `dedupe`, the eval set must reflect
the new behaviour. Add the new positive AND negative case to
`golden.json` **before** changing the code.
