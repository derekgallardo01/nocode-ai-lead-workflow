"""End-to-end lead intake pipeline: ingest → dedupe → classify → route.

Production "every morning, process yesterday's web-form + email leads"
workflow:

  1. Load raw leads from a JSON file (webforms, Calendly, business cards)
  2. Cross-channel dedupe (same email from form + email = one lead)
  3. Classify intent: pricing / demo / partnership / nurture / spam
  4. Summarize each lead's intent in one line
  5. Route confident classifications to the CRM; low-confidence -> human review
  6. Build a follow-up tasks list for the SDR team
  7. Emit per-lead JSON files (one per CRM record)

Runs against the bundled leads.json by default (B2B SaaS); pass
data/leads-real-estate.json to see the real-estate flow.

Usage:
    python examples/batch_lead_intake.py
    python examples/batch_lead_intake.py --leads data/leads-real-estate.json
    python examples/batch_lead_intake.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="End-to-end lead intake pipeline demo.")
    parser.add_argument("--leads", default="data/leads.json",
                        help="Path to leads JSON (default: bundled B2B SaaS leads).")
    parser.add_argument("--no-dedupe", action="store_true",
                        help="Skip cross-channel dedupe.")
    parser.add_argument("--no-review", action="store_true",
                        help="Skip routing to human review (everything goes to CRM).")
    parser.add_argument("--out", default=None,
                        help="Output directory. Default: temp dir cleaned at exit.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    cleanup_tmp = False
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="lead_intake_demo_"))
        cleanup_tmp = True

    try:
        report = run(
            args.leads, str(out_dir),
            do_dedupe=not args.no_dedupe,
            do_human_review=not args.no_review,
        )

        if args.json:
            print(json.dumps(report, indent=2, default=str))
            return 0

        # Human-readable report
        print(f"\n{'=' * 70}")
        print(f"Lead intake pipeline run: {args.leads}")
        print(f"{'=' * 70}\n")

        print(f"  Raw leads loaded:         {report.get('raw_leads', '?')}")
        print(f"  After dedupe:             {report.get('deduped_leads', '?')}")
        merged = report.get('merged_pairs', [])
        if merged:
            print(f"  Duplicate pairs merged:   {len(merged)}")
            for dup in merged[:3]:
                channels = ", ".join(dup.get('channels', []))
                print(f"    - {dup.get('email')}  ({dup.get('primary_id')} <- {dup.get('merged_id')}, "
                      f"channels: {channels})")

        crm_count = report.get('processed', 0)
        review_count = report.get('human_review', 0)
        print(f"\n  Routed to CRM:            {crm_count}")
        print(f"  Sent to human review:     {review_count}")
        print(f"  Follow-up drafts created: {report.get('follow_ups', 0)}")

        review_list = report.get('human_review_list', [])
        review_emails = {r.get('email') for r in review_list}
        processed_list = report.get('processed_list', [])
        if processed_list:
            print(f"\n  Sample processed leads (CRM-routed):")
            crm_routed = [p for p in processed_list
                          if getattr(p, 'email', '') not in review_emails]
            for p in crm_routed[:5]:
                email = getattr(p, 'email', '(no email)')
                category = getattr(p, 'category', '?')
                conf = getattr(p, 'confidence', '')
                print(f"    [CRM]    {email:35s} category={category:20s} conf={conf}")

        # Show review-queue entries (the human-touch ones)
        if review_list:
            print(f"\n  Human review queue ({len(review_list)}):")
            for r in review_list:
                print(f"    {r.get('email', '(no email)'):35s} {r.get('reason', '')}")

        print(f"\n  Output files: {out_dir}")
        if cleanup_tmp:
            print(f"  (Temp dir cleaned at exit; pass --out to keep.)")

    finally:
        if cleanup_tmp:
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
