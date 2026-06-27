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

    print(f"Processed {result['processed']} leads; "
          f"drafted {result['follow_ups']} follow-ups.\n")
    for p in result["processed_list"]:
        print(f"[{p.id}] {p.channel:9} {p.category:18} {p.name}")
        print(f"     summary: {p.summary}")
        if p.draft_reply:
            print(f"     reply  : {p.draft_reply[:80]}…")
        else:
            print("     reply  : (none — filtered as spam)")
    print(f"\nWrote CRM + follow-ups to: {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
