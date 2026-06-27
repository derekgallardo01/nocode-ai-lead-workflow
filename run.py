"""Demo the lead-handling workflow over sample leads."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import run  # noqa: E402


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "out")
    result = run(os.path.join(here, "data", "leads.json"), out)

    print(f"Raw leads: {result['raw_leads']}  |  After dedupe: {result['deduped_leads']}  "
          f"({len(result['merged_pairs'])} merged pair(s))")
    for pair in result["merged_pairs"]:
        print(f"  merged {pair['merged_id']} into {pair['primary_id']} "
              f"({pair['email']}; {' + '.join(pair['channels'])})")

    print(f"\nFollow-ups drafted: {result['follow_ups']}  |  "
          f"Human-review queue: {result['human_review']}\n")

    for p in result["processed_list"]:
        flag = "  [HUMAN-REVIEW]" if p.needs_human_review else ""
        merged = f"  (merged: {', '.join(p.merged_from)})" if p.merged_from else ""
        print(f"[{p.id}] {p.channel:9} {p.category:18} {p.name}{flag}{merged}")
        print(f"     summary: {p.summary}")
        if p.draft_reply and not p.needs_human_review:
            print(f"     reply  : {p.draft_reply[:80]}...")
        elif p.needs_human_review:
            print(f"     reply  : (none - flagged for human review, confidence={p.confidence})")
        else:
            print("     reply  : (none - filtered as spam)")

    if result["human_review_list"]:
        print(f"\nHuman-review queue ({result['human_review']}):")
        for q in result["human_review_list"]:
            print(f"  [{q['id']}] {q['name']} ({q['channel']}) - {q['reason']}")

    print(f"\nWrote CRM + follow-ups + human-review queue to: {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
