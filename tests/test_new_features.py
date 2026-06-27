import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pipeline import Lead, _classify, dedupe, process_leads, run  # noqa: E402

LEADS = os.path.join(ROOT, "data", "leads.json")


def _lead(id_, channel, name, email, message):
    return Lead(id=id_, channel=channel, name=name, email=email, message=message)


# --- dedupe -------------------------------------------------------------------

def test_dedupe_merges_same_email_across_channels():
    leads = [
        _lead("a", "web_form", "Dana", "dana@x.co", "form msg"),
        _lead("b", "email", "Dana", "dana@x.co", "email msg"),
    ]
    deduped, pairs = dedupe(leads)
    assert len(deduped) == 1 and deduped[0].id == "a"
    assert len(pairs) == 1
    assert pairs[0]["primary_id"] == "a" and pairs[0]["merged_id"] == "b"


def test_dedupe_treats_email_case_insensitive():
    leads = [
        _lead("a", "web_form", "Dana", "dana@x.co", "msg"),
        _lead("b", "email", "Dana", "Dana@X.CO", "msg"),
    ]
    deduped, pairs = dedupe(leads)
    assert len(deduped) == 1
    assert len(pairs) == 1


def test_dedupe_preserves_distinct_emails():
    leads = [
        _lead("a", "email", "X", "x@a.co", "m"),
        _lead("b", "email", "Y", "y@a.co", "m"),
    ]
    deduped, pairs = dedupe(leads)
    assert len(deduped) == 2 and pairs == []


def test_merged_from_appears_on_processed():
    leads = [
        _lead("a", "web_form", "Dana", "dana@x.co", "send a quote please"),
        _lead("b", "email", "Dana", "dana@x.co", "following up about pricing"),
    ]
    deduped, pairs = dedupe(leads)
    merged_into = {p["primary_id"]: [p["merged_id"]] for p in pairs}
    processed = process_leads(deduped, merged_into=merged_into)
    assert processed[0].merged_from == ["b"]


# --- human-review queue -------------------------------------------------------

def test_fallback_classification_flags_human_review():
    cat, conf, matches = _classify("Hi - just wanted to reach out and say hi.")
    assert conf == "fallback"
    assert matches == []
    processed = process_leads([
        _lead("vague", "email", "X", "x@y.z", "Hi - just wanted to reach out and say hi.")
    ])
    assert processed[0].needs_human_review is True


def test_strong_classification_does_not_flag_human_review():
    processed = process_leads([
        _lead("ok", "email", "X", "x@y.z", "Please send a quote for 50 seats - pricing for our team."),
    ])
    assert processed[0].needs_human_review is False
    assert processed[0].confidence == "strong"


def test_weak_classification_kept_in_normal_queue():
    # A single keyword in a normal category is weak but not flagged.
    processed = process_leads([
        _lead("weak", "email", "X", "x@y.z", "I need help with something on your platform.")
    ])
    assert processed[0].confidence == "weak"
    assert processed[0].needs_human_review is False


# --- end-to-end on the bundled sample -----------------------------------------

def test_sample_dataset_produces_expected_counts():
    out = tempfile.mkdtemp()
    r = run(LEADS, out)
    assert r["raw_leads"] == 9
    assert r["deduped_leads"] == 7
    assert len(r["merged_pairs"]) == 2
    # follow_ups = 7 - 1 spam - 1 human_review = 5
    assert r["follow_ups"] == 5
    assert r["human_review"] == 1


def test_human_review_queue_file_written():
    out = tempfile.mkdtemp()
    run(LEADS, out)
    path = os.path.join(out, "for_human_review.json")
    assert os.path.exists(path)
    queue = json.load(open(path))
    assert len(queue) == 1


def test_no_dedupe_keeps_duplicates_separate():
    out = tempfile.mkdtemp()
    r = run(LEADS, out, do_dedupe=False)
    assert r["deduped_leads"] == 9
    assert r["merged_pairs"] == []
    # No dedupe: 9 - 1 spam - 1 human-review = 7 (the two Danas + two Aishas all reply)
    assert r["follow_ups"] == 7


def test_no_human_review_routes_all_to_followups():
    out = tempfile.mkdtemp()
    r = run(LEADS, out, do_human_review=False)
    # The fallback-confidence lead becomes a normal follow-up now.
    assert r["human_review"] == 0
    assert r["follow_ups"] == 6  # 7 deduped - 1 spam
