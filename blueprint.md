# Blueprint — mapping the workflow onto no-code tools

`pipeline.py` proves the logic. This is how each step becomes a node in the tool a
client already pays for. The design is identical everywhere; only the node names
change.

## The five logical steps

1. **Trigger** — a new lead arrives (web form, email, or CRM record).
2. **AI step** — call an LLM to return `{summary, category, draft_reply}`.
   Categories: `quote_request`, `support_request`, `partnership`, `billing`,
   `spam_or_irrelevant`. Ambiguous → `support_request` (a human sees it).
3. **Persist** — append a row to the CRM / sheet (one row per lead, always — even
   spam, for the audit trail).
4. **Branch** — if `category == spam_or_irrelevant`, stop. Otherwise continue.
5. **Follow-up** — draft/queue an email to the lead using `draft_reply`.

## Node-by-node mapping

| Step | Make.com | Zapier | n8n | Power Automate |
|------|----------|--------|-----|----------------|
| 1 · Trigger | Webhook / Email / Watch Records | Catch Hook / New Email / New Record | Webhook / IMAP / CRM Trigger | When an HTTP request is received / When a new email arrives / When a row is added |
| 2 · AI step | OpenAI (Chat) module → parse JSON | OpenAI / ChatGPT action | OpenAI node (or HTTP Request) | "Create text with GPT" (Azure OpenAI / AI Builder) |
| 3 · Persist | Google Sheets / Airtable / CRM "Add a record" | Sheets / Airtable / CRM "Create" | Sheets / Postgres / CRM node | Add a row (Excel / Dataverse / SharePoint list) |
| 4 · Branch | Router + filter on category | Filter / Paths | IF node | Condition control |
| 5 · Follow-up | Email / Gmail / CRM "Send" | Email / Gmail action | Send Email node | Send an email (Outlook) |

## The AI step prompt (portable)

Use a system prompt that forces JSON so every tool can parse it the same way:

```
You are a lead-triage assistant. Given a customer message, respond with ONLY a JSON
object: {"summary": "...", "category": "...", "draft_reply": "..."}.
category must be one of: quote_request, support_request, partnership, billing,
spam_or_irrelevant. If unsure, use support_request. For spam_or_irrelevant, set
draft_reply to "".
```

In `pipeline.py` this is the deterministic `RULES` + `REPLY_TEMPLATES` stub so the
demo runs without a key; in production it's this one prompt to the client's model.

## Gotchas worth charging for (and why the code handles them)

- **Spam must still be logged, just not answered** — step 3 runs for every lead,
  step 5 is gated. (`save_crm` writes all; `follow_ups` skips spam.)
- **A safe default category** — never silently drop an unclassifiable lead; route
  it to a human. (`_classify` falls back to `support_request`.)
- **Idempotency / dedupe** — on re-runs, match on a lead id before inserting so you
  don't double-write or double-email. (Pair with an idempotent upsert keyed on a stable id.)
- **Reproducible JSON** — force the model to emit strict JSON so the parse step
  never breaks the flow.
