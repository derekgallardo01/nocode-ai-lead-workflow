"""Offline simulator of the lead-handling AI workflow.

Pattern: a lead arrives (form/email/CRM) → an LLM summarizes + categorizes +
drafts a reply → the result is saved to a CRM/sheet → a follow-up is queued.
Proves the logic that you'd wire in Make.com / Zapier / Power Automate.

Stdlib-only; deterministic local LLM stub by default. Set LLM_PROVIDER to route to
a real model (adapters wired, never called in the default path).
"""

from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import asdict, dataclass

CATEGORIES = ["quote_request", "support_request", "partnership", "billing",
              "spam_or_irrelevant"]

# Deterministic keyword rules for the stub classifier.
RULES = [
    ("quote_request", ["quote", "pricing", "price", "cost", "estimate", "buy", "demo"]),
    ("billing", ["invoice", "refund", "payment", "charge", "billing", "receipt"]),
    ("support_request", ["help", "issue", "broken", "error", "not working", "support", "bug"]),
    ("partnership", ["partner", "reseller", "collaborat", "affiliate", "white-label"]),
    ("spam_or_irrelevant", ["seo services", "rank your", "crypto", "loan offer"]),
]

REPLY_TEMPLATES = {
    "quote_request": "Thanks for your interest! I'd love to put together a quote — "
                     "could you share your team size and timeline?",
    "support_request": "Sorry you're hit a snag. I've logged this and our team will "
                       "follow up shortly — can you confirm what you were trying to do?",
    "partnership": "Thanks for reaching out about partnering. I'll route this to our "
                   "partnerships team and follow up to set a call.",
    "billing": "Thanks — I've flagged this to billing. We'll review your account and "
               "get back to you within one business day.",
    "spam_or_irrelevant": "",
}


@dataclass
class Lead:
    id: str
    channel: str
    name: str
    email: str
    message: str


@dataclass
class Processed:
    id: str
    channel: str
    name: str
    email: str
    category: str
    summary: str
    draft_reply: str


def _classify(text: str) -> str:
    t = text.lower()
    for cat, kws in RULES:
        if any(k in t for k in kws):
            return cat
    return "support_request"  # safe default — a human sees it


def _summarize(text: str, limit: int = 140) -> str:
    one = re.sub(r"\s+", " ", text).strip()
    return one if len(one) <= limit else one[:limit].rsplit(" ", 1)[0] + "…"


def complete(lead: Lead) -> tuple[str, str, str]:
    """Return (summary, category, draft_reply) for a lead.

    Default: deterministic local stub. LLM_PROVIDER=azure|anthropic routes to a
    real model (adapters defined below; not called in the default path).
    """
    provider = os.environ.get("LLM_PROVIDER", "local").lower()
    if provider in ("azure", "anthropic"):  # pragma: no cover - needs real key
        return _real_complete(provider, lead)
    cat = _classify(lead.message)
    return _summarize(lead.message), cat, REPLY_TEMPLATES[cat]


def _real_complete(provider, lead):  # pragma: no cover
    """Placeholder for a real LLM call (Azure OpenAI / Anthropic via urllib).

    Build a prompt asking for JSON {summary, category, draft_reply} and parse it.
    Intentionally not exercised offline; keeps the default path key-free.
    """
    raise RuntimeError("Set up the real LLM adapter and credentials to use "
                       f"provider={provider!r}.")


def process_leads(leads: list[Lead]) -> list[Processed]:
    out = []
    for lead in leads:
        summary, cat, reply = complete(lead)
        out.append(Processed(lead.id, lead.channel, lead.name, lead.email,
                             cat, summary, reply))
    return out


def save_crm(processed: list[Processed], out_dir: str) -> dict:
    """Persist results to a mock CRM/sheet (CSV + JSON)."""
    os.makedirs(out_dir, exist_ok=True)
    rows = [asdict(p) for p in processed]
    with open(os.path.join(out_dir, "crm.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)
    with open(os.path.join(out_dir, "crm.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return {"saved": len(rows)}


def follow_ups(processed: list[Processed]) -> list[dict]:
    """Draft a follow-up email for every lead that isn't spam."""
    drafts = []
    for p in processed:
        if p.category == "spam_or_irrelevant":
            continue
        drafts.append({
            "to": p.email,
            "subject": f"Re: your message ({p.category.replace('_', ' ')})",
            "body": f"Hi {p.name.split()[0]},\n\n{p.draft_reply}\n\nBest,\nThe Team",
        })
    return drafts


def run(leads_path: str, out_dir: str) -> dict:
    with open(leads_path, encoding="utf-8") as fh:
        leads = [Lead(**d) for d in json.load(fh)]
    processed = process_leads(leads)
    save_crm(processed, out_dir)
    drafts = follow_ups(processed)
    with open(os.path.join(out_dir, "follow_ups.json"), "w", encoding="utf-8") as fh:
        json.dump(drafts, fh, indent=2)
    return {"leads": len(leads), "processed": len(processed),
            "follow_ups": len(drafts), "processed_list": processed,
            "drafts": drafts}
