"""Offline simulator of the lead-handling AI workflow.

Pattern: a lead arrives (form/email/CRM) -> dedupe across channels -> LLM
summarizes + categorizes + drafts a reply -> the result is saved to a CRM/sheet
-> a follow-up is queued, OR the lead is routed to a human-review queue when
classification confidence is low. Proves the logic that you'd wire in
Make.com / Zapier / Power Automate.

Stdlib-only; deterministic local LLM stub by default. Set LLM_PROVIDER to route
to a real model (adapters wired, never called in the default path).
"""

from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import asdict, dataclass, field

CATEGORIES = ["quote_request", "support_request", "partnership", "billing",
              "spam_or_irrelevant"]

RULES = [
    ("quote_request", ["quote", "pricing", "price", "cost", "estimate", "buy", "demo", "seats", "enterprise plan"]),
    ("billing", ["invoice", "refund", "payment", "charge", "billing", "receipt", "charged"]),
    ("support_request", ["help", "issue", "broken", "error", "not working", "support", "bug", "asap"]),
    ("partnership", ["partner", "reseller", "collaborat", "affiliate", "white-label"]),
    ("spam_or_irrelevant", ["seo services", "rank your", "crypto", "loan offer", "cheap seo"]),
]

REPLY_TEMPLATES = {
    "quote_request": "Thanks for your interest! I'd love to put together a quote - "
                     "could you share your team size and timeline?",
    "support_request": "Sorry you're hit a snag. I've logged this and our team will "
                       "follow up shortly - can you confirm what you were trying to do?",
    "partnership": "Thanks for reaching out about partnering. I'll route this to our "
                   "partnerships team and follow up to set a call.",
    "billing": "Thanks - I've flagged this to billing. We'll review your account and "
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
    confidence: str = "strong"
    needs_human_review: bool = False
    matched_keywords: list[str] = field(default_factory=list)
    merged_from: list[str] = field(default_factory=list)


def _classify(text: str) -> tuple[str, str, list[str]]:
    """Return (category, confidence, matched_keywords).

    confidence is one of:
      - "strong"   : 2+ keyword matches in one category
      - "weak"     : exactly 1 keyword matched
      - "fallback" : no keywords matched; default category was used
    """
    t = text.lower()
    for cat, kws in RULES:
        matches = [k for k in kws if k in t]
        if matches:
            return cat, ("strong" if len(matches) >= 2 else "weak"), matches
    return "support_request", "fallback", []


def _summarize(text: str, limit: int = 140) -> str:
    one = re.sub(r"\s+", " ", text).strip()
    return one if len(one) <= limit else one[:limit].rsplit(" ", 1)[0] + "..."


def complete(lead: Lead) -> tuple[str, str, str]:
    """Return (summary, category, draft_reply) for a lead.

    Default: deterministic local stub. LLM_PROVIDER=azure|anthropic routes to a
    real model (adapters defined below; not called in the default path).
    """
    provider = os.environ.get("LLM_PROVIDER", "local").lower()
    if provider in ("azure", "anthropic"):  # pragma: no cover - needs real key
        return _real_complete(provider, lead)
    cat, _conf, _matches = _classify(lead.message)
    return _summarize(lead.message), cat, REPLY_TEMPLATES[cat]


def _real_complete(provider, lead):  # pragma: no cover
    raise RuntimeError("Set up the real LLM adapter and credentials to use "
                       f"provider={provider!r}.")


def _norm_email(email: str) -> str:
    return email.strip().lower()


def dedupe(leads: list[Lead]) -> tuple[list[Lead], list[dict]]:
    """Collapse leads that share a normalized email.

    Keeps the first occurrence (in input order) and records each merged pair so
    the audit trail isn't lost.
    """
    seen: dict[str, Lead] = {}
    order: list[Lead] = []
    merged_into: dict[str, list[str]] = {}
    pairs: list[dict] = []
    for lead in leads:
        key = _norm_email(lead.email)
        if key in seen:
            primary = seen[key]
            merged_into.setdefault(primary.id, []).append(lead.id)
            pairs.append({
                "primary_id": primary.id, "merged_id": lead.id,
                "email": key, "channels": [primary.channel, lead.channel],
            })
        else:
            seen[key] = lead
            order.append(lead)
    return order, pairs


def process_leads(leads: list[Lead],
                  merged_into: dict[str, list[str]] | None = None
                  ) -> list[Processed]:
    merged_into = merged_into or {}
    out = []
    for lead in leads:
        cat, conf, matches = _classify(lead.message)
        summary = _summarize(lead.message)
        reply = REPLY_TEMPLATES.get(cat, "")
        needs_review = (
            conf == "fallback"
            or (cat == "spam_or_irrelevant" and conf == "weak")
        )
        out.append(Processed(
            id=lead.id, channel=lead.channel, name=lead.name, email=lead.email,
            category=cat, summary=summary, draft_reply=reply,
            confidence=conf, needs_human_review=needs_review,
            matched_keywords=matches,
            merged_from=merged_into.get(lead.id, []),
        ))
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
    """Draft a follow-up for every lead that isn't spam and isn't queued for human review."""
    drafts = []
    for p in processed:
        if p.category == "spam_or_irrelevant":
            continue
        if p.needs_human_review:
            continue
        drafts.append({
            "to": p.email,
            "subject": f"Re: your message ({p.category.replace('_', ' ')})",
            "body": f"Hi {p.name.split()[0]},\n\n{p.draft_reply}\n\nBest,\nThe Team",
        })
    return drafts


def human_review_queue(processed: list[Processed]) -> list[dict]:
    """Leads that need a human eye before any reply goes out."""
    queue = []
    for p in processed:
        if not p.needs_human_review:
            continue
        queue.append({
            "id": p.id, "name": p.name, "email": p.email, "channel": p.channel,
            "summary": p.summary, "category": p.category,
            "confidence": p.confidence, "matched_keywords": p.matched_keywords,
            "reason": ("no rule matched; routed to default"
                       if p.confidence == "fallback"
                       else "only a weak match - confirm before reply"),
        })
    return queue


def run(leads_path: str, out_dir: str,
        do_dedupe: bool = True, do_human_review: bool = True) -> dict:
    with open(leads_path, encoding="utf-8") as fh:
        raw_leads = [Lead(**d) for d in json.load(fh)]

    if do_dedupe:
        leads, pairs = dedupe(raw_leads)
    else:
        leads, pairs = raw_leads, []
    merged_into = {p["primary_id"]: [] for p in pairs}
    for p in pairs:
        merged_into[p["primary_id"]].append(p["merged_id"])

    processed = process_leads(leads, merged_into=merged_into)
    if not do_human_review:
        for p in processed:
            p.needs_human_review = False

    save_crm(processed, out_dir)
    drafts = follow_ups(processed)
    queue = human_review_queue(processed)

    with open(os.path.join(out_dir, "follow_ups.json"), "w", encoding="utf-8") as fh:
        json.dump(drafts, fh, indent=2)
    with open(os.path.join(out_dir, "for_human_review.json"), "w", encoding="utf-8") as fh:
        json.dump(queue, fh, indent=2)

    return {
        "raw_leads": len(raw_leads),
        "deduped_leads": len(leads),
        "merged_pairs": pairs,
        "processed": len(processed),
        "processed_list": processed,
        "follow_ups": len(drafts),
        "drafts": drafts,
        "human_review": len(queue),
        "human_review_list": queue,
        # Back-compat keys for existing test code:
        "leads": len(raw_leads),
    }
