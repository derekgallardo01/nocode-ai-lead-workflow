"""Run the workflow against the golden eval set.

    python evals/run.py

Exit code 0 if every case behaves as expected, 1 otherwise. Each case is
either an inline list of leads OR a path to a leads JSON file, with the
expected counts and category distribution.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pipeline import Lead, dedupe, process_leads  # noqa: E402
from pipeline import run as pipeline_run  # noqa: E402


def _execute(case: dict) -> dict:
    if "leads_path" in case:
        path = os.path.join(ROOT, case["leads_path"])
        out = tempfile.mkdtemp()
        return pipeline_run(path, out)

    leads = [Lead(**d) for d in case["leads"]]
    deduped, pairs = dedupe(leads)
    merged_into = {p["primary_id"]: [p["merged_id"]] for p in pairs}
    processed = process_leads(deduped, merged_into=merged_into)
    follow_ups = [
        p for p in processed
        if p.category != "spam_or_irrelevant" and not p.needs_human_review
    ]
    human_review = [p for p in processed if p.needs_human_review]
    return {
        "raw_leads": len(leads),
        "deduped_leads": len(deduped),
        "merged_pairs": pairs,
        "processed_list": processed,
        "follow_ups": len(follow_ups),
        "human_review": len(human_review),
    }


def _check(case: dict, result: dict) -> list[str]:
    expect = case["expect"]
    details: list[str] = []
    if "raw_leads" in expect and result.get("raw_leads") != expect["raw_leads"]:
        details.append(f"raw_leads={result.get('raw_leads')} expected={expect['raw_leads']}")
    if "deduped" in expect and result.get("deduped_leads") != expect["deduped"]:
        details.append(f"deduped={result.get('deduped_leads')} expected={expect['deduped']}")
    if "merged_pairs" in expect and len(result.get("merged_pairs", [])) != expect["merged_pairs"]:
        details.append(f"merged_pairs={len(result.get('merged_pairs', []))} expected={expect['merged_pairs']}")
    if "follow_ups" in expect and result.get("follow_ups") != expect["follow_ups"]:
        details.append(f"follow_ups={result.get('follow_ups')} expected={expect['follow_ups']}")
    if "human_review" in expect and result.get("human_review") != expect["human_review"]:
        details.append(f"human_review={result.get('human_review')} expected={expect['human_review']}")
    if "categories" in expect:
        actual = Counter(p.category for p in result["processed_list"])
        for cat, n in expect["categories"].items():
            if actual.get(cat, 0) != n:
                details.append(f"category[{cat}]={actual.get(cat, 0)} expected={n}")
    return details


def main() -> int:
    with open(os.path.join(HERE, "golden.json"), encoding="utf-8") as fh:
        cases = json.load(fh)

    passed, failed = [], []
    for case in cases:
        result = _execute(case)
        details = _check(case, result)
        rec = {"id": case["id"], "details": details}
        (passed if not details else failed).append(rec)

    total = len(cases)
    rate = (len(passed) / total * 100) if total else 0.0
    print(f"Eval: {len(passed)}/{total} passed ({rate:.0f}%)")
    if failed:
        print(f"\n{len(failed)} failed:")
        for f in failed:
            print(f"  [{f['id']}]")
            for d in f["details"]:
                print(f"       {d}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
