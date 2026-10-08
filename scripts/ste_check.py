#!/usr/bin/env python3
"""ste_check.py - verify an STE render file outside the model.

Checks a render file (Markdown with fixed sections) for:
  1. Fact retention: every claim anchor and preserved term from the dense
     original must appear verbatim in the STE view.        -> error
  2. Hedge retention: if/unless/not/... must not silently disappear. -> warning
  3. STE writing limits on the STE view (sentence length, paragraph length,
     semicolons, passive voice, wordy phrases).   -> error (strict) / warning (--soft)
  4. Diagram edges: every Mermaid edge has a matching sentence. -> error

It can also check an HTML page for a visible assumptions panel.

What it does NOT check: the ASD-STE100 dictionary (about 900 approved words)
is copyrighted and not bundled, so vocabulary compliance is not verified.
A pass means "these configured rules hold", not "this is certified STE".

Stdlib only. Exit code 0 = no errors, 1 = errors, 2 = bad input.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path

# --- limits (paraphrased from ASD-STE100 Issue 9; see references/writing-rules.md)
PROCEDURAL_MAX_WORDS = 20
DESCRIPTIVE_MAX_WORDS = 25
PARAGRAPH_MAX_SENTENCES = 6

HEDGES = ["if", "unless", "not", "only", "may", "might", "except",
          "until", "without", "never", "no", "cannot", "unverified"]

# House list of wordy phrases. NOT the ASD dictionary. Kept deliberately short
# so it never bans a word the standard approves (e.g. "approximately").
WORDY = {
    "in order to": "to",
    "prior to": "before",
    "utilize": "use",
    "utilise": "use",
    "leverage": "use",
    "facilitate": "help / make possible",
    "commence": "start",
    "due to the fact that": "because",
    "in the event that": "if",
    "it is imperative that": "(state the instruction directly)",
    "a number of": "some / <exact number>",
    "with regard to": "about",
}

IRREGULAR_PARTICIPLES = {
    "built", "done", "made", "known", "written", "given", "taken", "seen",
    "shown", "sent", "kept", "held", "found", "chosen", "drawn", "broken",
    "hidden", "thrown", "frozen", "spoken", "driven", "begun", "brought",
    "bought", "caught", "taught", "thought", "left", "lost", "meant", "paid",
    "read", "said", "sold", "told", "understood", "won", "split", "shut",
}
PASSIVE_RE = re.compile(
    r"\b(am|is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?(\w+ed|"
    + "|".join(sorted(IRREGULAR_PARTICIPLES)) + r")\b",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’_.%/\-]*")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"(\[])")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
LIST_RE = re.compile(r"^\s*(?:(\d+)[.)]|[-*+])\s+")


@dataclass
class Finding:
    level: str      # "error" | "warning"
    check: str      # e.g. "fact-retention"
    message: str
    line: int | None = None


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------
def split_sections(text: str) -> dict[str, tuple[str, int]]:
    """Return {lowercased '## heading': (body, first_body_line_number)}."""
    sections: dict[str, tuple[str, int]] = {}
    current, buf, start = None, [], 0
    in_fence = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            if current is not None:
                sections[current] = ("\n".join(buf), start)
            current, buf, start = line[3:].strip().lower(), [], i + 1
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = ("\n".join(buf), start)
    return sections


def strip_code(text: str) -> str:
    """Remove fenced blocks (keep line count) and turn inline code into one token."""
    text = FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return INLINE_CODE_RE.sub("CODE", text)


def parse_list_items(body: str) -> list[str]:
    return [LIST_RE.sub("", l).strip() for l in body.splitlines() if LIST_RE.match(l)]


def parse_claims(body: str) -> list[dict]:
    m = re.search(r"```json\s*(.*?)```", body, re.DOTALL)
    if not m:
        raise ValueError("'## Claims' must contain a ```json block")
    claims = json.loads(m.group(1))
    if not isinstance(claims, list):
        raise ValueError("Claims JSON must be a list")
    return claims


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------
def anchor_present(anchor: str, haystack: str) -> bool:
    if anchor in haystack:
        return True
    # Plain words may move to sentence start and change case.
    if re.fullmatch(r"[A-Za-z][A-Za-z \-]*", anchor):
        return re.search(r"\b" + re.escape(anchor) + r"\b", haystack, re.IGNORECASE) is not None
    return False


def check_retention(claims, preserved, ste_raw) -> list[Finding]:
    out = []
    for c in claims:
        cid = c.get("id", "?")
        anchors = c.get("anchors") or []
        if not anchors:
            out.append(Finding("warning", "fact-retention",
                               f"{cid} has no anchors, so it cannot be verified: {c.get('claim', '')!r}"))
        for a in anchors:
            if not anchor_present(a, ste_raw):
                out.append(Finding("error", "fact-retention",
                                   f"{cid} dropped: anchor {a!r} is missing from the STE view "
                                   f"(claim: {c.get('claim', '')!r})"))
    for term in preserved:
        t = term.strip("`")
        if t and t not in ste_raw:
            out.append(Finding("error", "preserved-term",
                               f"preserved term {t!r} is missing or changed in the STE view"))
    return out


def count_words(s: str, words: list[str]) -> dict[str, int]:
    low = s.lower()
    return {w: len(re.findall(r"\b" + re.escape(w) + r"\b", low)) for w in words}


def check_hedges(original: str, ste: str) -> list[Finding]:
    a, b = count_words(strip_code(original), HEDGES), count_words(strip_code(ste), HEDGES)
    out = []
    for w in HEDGES:
        # contractions ("isn't", "can't") also carry "not"
        if w == "not":
            a[w] += len(re.findall(r"n['’]t\b", original.lower()))
            b[w] += len(re.findall(r"n['’]t\b", ste.lower()))
        if b[w] < a[w]:
            out.append(Finding("warning", "hedge",
                               f"{w!r} appears {a[w]}x in the original but {b[w]}x in the STE view. "
                               f"Check that no condition or negation was dropped."))
    return out


def check_style(ste: str, start_line: int, soft: bool) -> list[Finding]:
    hard = "warning" if soft else "error"
    out: list[Finding] = []
    clean = strip_code(ste)
    # Mermaid/edge sections are excluded by the caller; here we walk blocks.
    lines = clean.splitlines()
    block: list[tuple[int, str]] = []

    def flush():
        if not block:
            return
        is_list = all(LIST_RE.match(t) for _, t in block if t.strip())
        units = []  # (line, text, procedural)
        if is_list:
            for ln, t in block:
                m = LIST_RE.match(t)
                procedural = bool(m and m.group(1))
                units.append((ln, LIST_RE.sub("", t), procedural))
        else:
            units.append((block[0][0], " ".join(t.strip() for _, t in block), False))
        para_sentences = 0
        for ln, text, procedural in units:
            sentences = [s for s in SENT_SPLIT_RE.split(text.strip()) if s.strip()]
            para_sentences += len(sentences)
            limit = PROCEDURAL_MAX_WORDS if procedural else DESCRIPTIVE_MAX_WORDS
            kind = "procedural" if procedural else "descriptive"
            for s in sentences:
                n = len(WORD_RE.findall(s))
                if n > limit:
                    out.append(Finding(hard, "sentence-length",
                                       f"{kind} sentence has {n} words (max {limit}): {s[:80]!r}...", ln))
                for m in PASSIVE_RE.finditer(s):
                    # STE: procedural text uses active voice; descriptive text may use
                    # passive only when the agent is unknown -> we can't detect that, so warn.
                    lvl = hard if procedural else "warning"
                    out.append(Finding(lvl, "passive-voice",
                                       f"possible passive voice {m.group(0)!r} in {kind} text", ln))
        if not is_list and para_sentences > PARAGRAPH_MAX_SENTENCES:
            out.append(Finding(hard, "paragraph-length",
                               f"paragraph has {para_sentences} sentences (max {PARAGRAPH_MAX_SENTENCES})",
                               block[0][0]))
        block.clear()

    for i, raw in enumerate(lines):
        ln = start_line + i
        if not raw.strip() or raw.lstrip().startswith(("#", ">", "|")):
            flush()
            continue
        if ";" in raw:
            out.append(Finding(hard, "semicolon", "semicolon found, split into two sentences", ln))
        low = raw.lower()
        for phrase, repl in WORDY.items():
            if re.search(r"\b" + re.escape(phrase) + r"\b", low):
                out.append(Finding("warning", "wordy",
                                   f"{phrase!r} -> use {repl!r} (house list, not the ASD dictionary)", ln))
        block.append((ln, raw))
    flush()
    return out


# --- diagrams ---------------------------------------------------------------
ARROW_RE = re.compile(r"\s*(?:-\.->|-->|---|==>|--x|--o|-\.-)\s*")
SHAPE_RE = re.compile(r"\b([A-Za-z_][\w]*)\s*(\[\[|\[\(|\(\(|\[|\(|\{\{|\{|>)(.*?)(\]\]|\)\]|\)\)|\]|\)|\}\}|\})")
EDGE_LABEL_RE = re.compile(r"\|[^|]*\|")


def parse_mermaid(src: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    labels: dict[str, str] = {}
    edges: list[tuple[str, str]] = []
    for line in src.splitlines():
        line = line.strip()
        if not line or line.startswith(("%%", "graph", "flowchart", "classDef", "class ",
                                         "style ", "subgraph", "end", "linkStyle")):
            continue

        def keep_id(m):
            labels.setdefault(m.group(1), m.group(3).strip().strip('"'))
            return m.group(1)

        line = SHAPE_RE.sub(keep_id, line)
        line = EDGE_LABEL_RE.sub("", line)
        parts = [p.strip() for p in ARROW_RE.split(line)]
        if len(parts) < 2:
            continue
        for a, b in zip(parts, parts[1:]):
            if re.fullmatch(r"[A-Za-z_]\w*", a) and re.fullmatch(r"[A-Za-z_]\w*", b):
                edges.append((a, b))
    return labels, edges


def check_diagram(ste: str, edges_body: str | None) -> list[Finding]:
    blocks = re.findall(r"```mermaid\s*(.*?)```", ste, re.DOTALL)
    if not blocks:
        return []
    labels, edges = {}, []
    for b in blocks:
        l, e = parse_mermaid(b)
        labels.update(l)
        edges.extend(e)
    if edges_body is None:
        return [Finding("error", "diagram-edges",
                        f"diagram has {len(edges)} edges but no '## Edges' section")]
    items = [i.lower() for i in parse_list_items(edges_body)]

    def mentions(item: str, names: set[str]) -> bool:
        return any(re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", item) for n in names)

    out = []
    for a, b in edges:
        names_a = {a.lower(), labels.get(a, a).lower()}
        names_b = {b.lower(), labels.get(b, b).lower()}
        if not any(mentions(it, names_a) and mentions(it, names_b) for it in items):
            out.append(Finding("error", "diagram-edges",
                               f"edge {labels.get(a, a)!r} -> {labels.get(b, b)!r} has no sentence in '## Edges'"))
    if len(items) < len(edges):
        out.append(Finding("warning", "diagram-edges",
                           f"{len(edges)} edges but only {len(items)} edge sentences"))
    return out


# --- html -------------------------------------------------------------------
class _AssumptionsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0          # >0 while inside #assumptions
        self.found = False
        self.items = 0

    def handle_starttag(self, tag, attrs):
        if self.depth:
            self.depth += 1
            if tag == "li":
                self.items += 1
        elif dict(attrs).get("id") == "assumptions":
            self.found, self.depth = True, 1

    def handle_endtag(self, tag):
        if self.depth:
            self.depth -= 1


def check_html(text: str) -> list[Finding]:
    p = _AssumptionsParser()
    p.feed(text)
    if not p.found:
        return [Finding("error", "html-assumptions",
                        'page has no element with id="assumptions"; list the model\'s assumptions visibly')]
    if p.items == 0:
        return [Finding("error", "html-assumptions", "#assumptions has no <li> items")]
    return []


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------
def check_render(text: str, soft: bool = False) -> list[Finding]:
    s = split_sections(text)
    missing = [k for k in ("original", "ste view", "claims") if k not in s]
    if missing:
        raise ValueError(f"missing section(s): {', '.join('## ' + m.title() for m in missing)}")
    original, _ = s["original"]
    ste, ste_line = s["ste view"]
    claims = parse_claims(s["claims"][0])
    preserved = parse_list_items(s["preserved terms"][0]) if "preserved terms" in s else []
    edges_body = s["edges"][0] if "edges" in s else None

    findings = []
    findings += check_retention(claims, preserved, ste)
    findings += check_hedges(original, ste)
    findings += check_style(ste, ste_line, soft)
    findings += check_diagram(ste, edges_body)
    return findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path", help="render .md file, or .html page")
    ap.add_argument("--soft", action="store_true",
                    help="'80%% STE': style limits become warnings; fact retention stays an error")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    path = Path(args.path)
    try:
        text = path.read_text(encoding="utf-8")
        findings = check_html(text) if path.suffix.lower() in (".html", ".htm") \
            else check_render(text, soft=args.soft)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"ste_check: {path}: {e}", file=sys.stderr)
        return 2

    errors = [f for f in findings if f.level == "error"]
    if args.json:
        print(json.dumps({"file": str(path), "errors": len(errors),
                          "warnings": len(findings) - len(errors),
                          "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        for f in findings:
            loc = f"{path}:{f.line}" if f.line else str(path)
            print(f"{loc}: {f.level}: [{f.check}] {f.message}")
        mode = "soft" if args.soft else "strict"
        print(f"\n{len(errors)} error(s), {len(findings) - len(errors)} warning(s) [{mode}]. "
              f"Vocabulary is not checked (ASD dictionary not bundled).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
