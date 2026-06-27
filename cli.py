"""Process a custom leads file through the workflow.

    python cli.py path/to/leads.json
    python cli.py path/to/leads.json --out custom-out/
    python cli.py path/to/leads.json --no-dedupe
    python cli.py path/to/leads.json --no-human-review
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pipeline import run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Run the lead-handling workflow over a leads JSON file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("leads_path", help="Path to a leads JSON file.")
    p.add_argument("--out", default=os.path.join(HERE, "out"),
                   help="Output directory for CRM + follow-ups + human-review queue.")
    p.add_argument("--no-dedupe", action="store_true",
                   help="Skip cross-channel deduplication.")
    p.add_argument("--no-human-review", action="store_true",
                   help="Skip routing low-confidence leads to the human-review queue.")
    args = p.parse_args(argv)

    result = run(args.leads_path, args.out,
                 do_dedupe=not args.no_dedupe,
                 do_human_review=not args.no_human_review)

    by_channel = Counter(p.channel for p in result["processed_list"])
    by_category = Counter(p.category for p in result["processed_list"])

    print(f"Raw leads: {result['raw_leads']}  |  After dedupe: {result['deduped_leads']}  "
          f"({len(result['merged_pairs'])} merged pair(s))")
    if result["merged_pairs"]:
        for pair in result["merged_pairs"]:
            print(f"  merged {pair['merged_id']} into {pair['primary_id']} "
                  f"({pair['email']}; {' + '.join(pair['channels'])})")

    print(f"\nBy channel: " + ", ".join(f"{ch}={n}" for ch, n in sorted(by_channel.items())))
    print(f"By category: " + ", ".join(f"{c}={n}" for c, n in sorted(by_category.items())))

    print(f"\nFollow-ups drafted: {result['follow_ups']}  |  "
          f"Human-review queue: {result['human_review']}")
    if result["human_review_list"]:
        for q in result["human_review_list"]:
            print(f"  [{q['id']}] {q['name']} ({q['channel']}) - {q['reason']}")
    print(f"\nWrote CRM + follow-ups + human-review queue to: {args.out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
