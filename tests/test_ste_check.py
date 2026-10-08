"""Tests for scripts/ste_check.py. Run: python -m pytest -q"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ste_check as sc  # noqa: E402


def render(ste, original="Original text.", claims="[]", preserved="", edges=None):
    parts = ["# t", "## Original", original, "## STE view", ste]
    if edges is not None:
        parts += ["## Edges", edges]
    if preserved:
        parts += ["## Preserved terms", preserved]
    parts += ["## Claims", "```json\n" + claims + "\n```"]
    return "\n\n".join(parts)


def checks(findings, level="error"):
    return {f.check for f in findings if f.level == level}


# --- examples must pass -----------------------------------------------------
@pytest.mark.parametrize("name", ["weight-tying.md", "voice-agent-pipeline.md", "kv-cache-sizing.html"])
def test_examples_pass(name):
    assert sc.main([str(ROOT / "examples" / name)]) == 0


# --- fact retention (the core check) ----------------------------------------
def test_missing_anchor_is_error():
    f = sc.check_render(render("The model is small.",
                               claims='[{"id":"C1","claim":"124M params","anchors":["124M"]}]'))
    assert "fact-retention" in checks(f)


def test_anchor_case_insensitive_for_plain_words_only():
    ok = render("Regularizer effects exist.", claims='[{"id":"C1","claim":"x","anchors":["regularizer"]}]')
    assert "fact-retention" not in checks(sc.check_render(ok))
    bad = render("Use `wte` here.", claims='[{"id":"C1","claim":"x","anchors":["WTE_2"]}]')
    assert "fact-retention" in checks(sc.check_render(bad))  # identifiers stay case-sensitive


# --- anchors match whole tokens, not substrings (regression) ----------------
@pytest.mark.parametrize("anchor,text", [
    ("3", "Retry 300 times."),          # number inside a bigger number
    ("8", "The pool has 18 workers."),
    ("3", "Use version 1.3 now."),      # digit inside a version
    ("3", "Wait 3.5 seconds."),         # digit inside a decimal
    ("my_var", "Set my_var2 first."),   # identifier inside a longer one
    ("REQUEST_TIMEOUT_S", "Set REQUEST_TIMEOUT now."),
])
def test_anchor_does_not_match_inside_longer_token(anchor, text):
    assert not sc.anchor_present(anchor, text)


@pytest.mark.parametrize("anchor,text", [
    ("3", "Retry 3 times."),
    ("my_var", "Set my_var."),          # sentence-final period
    ("200ms", "Wait 200 ms first."),    # unit spacing differs
    ("200 ms", "Wait 200ms first."),
    ("unless", "Unless the key is set, stop."),  # plain word, case moved
    ("--soft", "Run with --soft for 80% mode."),
])
def test_anchor_matches_legit_forms(anchor, text):
    assert sc.anchor_present(anchor, text)


def test_preserved_term_is_case_sensitive():
    f = sc.check_retention([], ["`Redis`"], "We use redis here.")
    assert "preserved-term" in checks(f)


def test_claim_without_anchor_warns():
    f = sc.check_render(render("Text.", claims='[{"id":"C1","claim":"vague","anchors":[]}]'))
    assert "fact-retention" in checks(f, "warning")


def test_changed_preserved_term_is_error():
    f = sc.check_render(render("Set `max_tokens` to 512.", preserved="- `max_new_tokens`"))
    assert "preserved-term" in checks(f)


# --- hedges -------------------------------------------------------------------
def test_dropped_negation_warns():
    f = sc.check_render(render("The cache is safe.", original="The cache is not safe unless locked."))
    msgs = " ".join(x.message for x in f if x.check == "hedge")
    assert "'not'" in msgs and "'unless'" in msgs


def test_contraction_counts_as_not():
    f = sc.check_render(render("It does not retry.", original="It doesn't retry."))
    assert "hedge" not in checks(f, "warning")


# --- style --------------------------------------------------------------------
LONG = " ".join(["word"] * 26) + "."


def test_long_descriptive_sentence_is_error_strict_warning_soft():
    assert "sentence-length" in checks(sc.check_render(render(LONG)))
    assert "sentence-length" in checks(sc.check_render(render(LONG), soft=True), "warning")
    assert "sentence-length" not in checks(sc.check_render(render(LONG), soft=True))


def test_procedural_limit_is_20():
    step = "1. " + " ".join(["do"] * 21) + "."
    assert "sentence-length" in checks(sc.check_render(render(step)))
    desc = " ".join(["do"] * 21) + "."
    assert "sentence-length" not in checks(sc.check_render(render(desc)))


def test_semicolon_error():
    assert "semicolon" in checks(sc.check_render(render("Run it; then stop.")))


def test_paragraph_over_six_sentences():
    para = " ".join(["It runs."] * 7)
    assert "paragraph-length" in checks(sc.check_render(render(para)))


def test_passive_error_in_procedure_warning_in_description():
    assert "passive-voice" in checks(sc.check_render(render("1. The file is deleted by the job.")))
    f = sc.check_render(render("The file is deleted at midnight."))
    assert "passive-voice" in checks(f, "warning") and "passive-voice" not in checks(f)


def test_code_is_ignored_by_style():
    ste = "Run this.\n\n```python\nx = 1; y = 2  # " + " ".join(["w"] * 40) + "\n```"
    assert not checks(sc.check_render(render(ste)))


def test_wordy_is_warning_and_approximately_is_allowed():
    f = sc.check_render(render("Wait approximately 10 minutes in order to cool."))
    assert "wordy" in checks(f, "warning")
    assert not any("approximately" in x.message for x in f)


# --- diagrams -----------------------------------------------------------------
DIAGRAM = "```mermaid\nflowchart LR\n  A[Client] --> B[API]\n  B --> C[(DB)]\n```"


def test_diagram_needs_edges_section():
    assert "diagram-edges" in checks(sc.check_render(render(DIAGRAM)))


def test_diagram_edge_without_sentence_is_error():
    f = sc.check_render(render(DIAGRAM, edges="- The client calls the API."))
    msgs = [x.message for x in f if x.check == "diagram-edges" and x.level == "error"]
    assert len(msgs) == 1 and "'API' -> 'DB'" in msgs[0]


def test_diagram_all_edges_described_passes():
    f = sc.check_render(render(DIAGRAM, edges="- The client calls the API.\n- The API writes to the DB."))
    assert "diagram-edges" not in checks(f)


def test_mermaid_chain_and_labels():
    labels, edges = sc.parse_mermaid("A[x] --> B -->|yes| C\nC -.-> A")
    assert edges == [("A", "B"), ("B", "C"), ("C", "A")]
    assert labels["A"] == "x"


# --- html ---------------------------------------------------------------------
def test_html_requires_assumptions():
    assert "html-assumptions" in checks(sc.check_html("<html><body><p>hi</p></body></html>"))
    assert "html-assumptions" in checks(sc.check_html('<section id="assumptions"></section>'))
    assert not sc.check_html('<section id="assumptions"><ul><li>a</li></ul></section>')


# --- input errors -------------------------------------------------------------
def test_missing_section_exit_2(tmp_path):
    p = tmp_path / "bad.md"
    p.write_text("## Original\nx\n")
    assert sc.main([str(p)]) == 2


def test_dense_original_fails_as_ste_view():
    """The dense paragraph from the example must NOT pass as an STE view."""
    text = (ROOT / "examples" / "weight-tying.md").read_text()
    dense = sc.split_sections(text)["original"][0]
    f = sc.check_render(render(dense))
    assert {"sentence-length", "semicolon"} <= checks(f)
