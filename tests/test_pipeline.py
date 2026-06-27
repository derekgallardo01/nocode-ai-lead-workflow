import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pipeline import CATEGORIES, Lead, complete, run  # noqa: E402

LEADS = os.path.join(ROOT, "data", "leads.json")


def test_every_lead_gets_summary_and_category():
    out = tempfile.mkdtemp()
    r = run(LEADS, out)
    assert r["leads"] == r["raw_leads"] == 9
    assert r["processed"] == r["deduped_leads"] == 7
    for p in r["processed_list"]:
        assert p.summary
        assert p.category in CATEGORIES


def test_classification_rules():
    assert complete(Lead("x", "email", "A", "a@b.c", "please send a quote"))[1] == "quote_request"
    assert complete(Lead("x", "email", "A", "a@b.c", "I was charged twice, need a refund"))[1] == "billing"
    assert complete(Lead("x", "email", "A", "a@b.c", "the export is broken with an error"))[1] == "support_request"
    assert complete(Lead("x", "email", "A", "a@b.c", "reseller partnership opportunity"))[1] == "partnership"


def test_results_persisted():
    out = tempfile.mkdtemp()
    run(LEADS, out)
    assert os.path.exists(os.path.join(out, "crm.csv"))
    assert os.path.exists(os.path.join(out, "crm.json"))
    assert os.path.exists(os.path.join(out, "follow_ups.json"))


def test_follow_ups_skip_spam_and_human_review():
    out = tempfile.mkdtemp()
    r = run(LEADS, out)
    # 9 raw → 7 deduped, 1 spam excluded + 1 human-review excluded = 5 follow-ups
    assert r["follow_ups"] == 5
    assert r["human_review"] == 1
    assert all(d["body"].startswith("Hi ") for d in r["drafts"])


def test_deterministic():
    out1, out2 = tempfile.mkdtemp(), tempfile.mkdtemp()
    a = run(LEADS, out1)["processed_list"]
    b = run(LEADS, out2)["processed_list"]
    assert [p.category for p in a] == [p.category for p in b]
