---
name: ste-render
description: Render dense technical output into a human-readable view (ASD-STE100-style Simplified Technical English, a Mermaid diagram, or an interactive HTML page) and verify it with a checker so no facts, identifiers, numbers or conditions get lost. Use whenever the user asks to "explain simply", "explain in STE", "ASD-STE100", "80% STE", "plain English version", "make this readable", "draw this", "diagram this", "explain in HTML", or says an answer or document is too dense, even if they don't name STE. Also use before handing a long technical explanation, design doc, incident summary or code walkthrough to a human reader.
---

# ste-render

Turn dense output into something a human can read fast, without losing facts.

The idea comes from Andrej Karpathy's 2 Oct 2026 post: ask models for ASD-STE100
writing, then diagrams, then HTML. The risk with all three is the same. A cleaner
format can drop a fact or a condition and still look right. This skill fixes that
by making every render pass a checker that runs outside the model.

## Core rules

1. **Render at the boundary, not in your reasoning.** Think, plan and write code in
   your normal dense style. Apply this skill only to the text a human will read.
2. **Never replace the original.** Every render keeps the dense original next to the
   simplified view.
3. **The checker decides, not you.** Never tell the user the text "is STE" or "is
   compliant". Report what `scripts/ste_check.py` said. It does not check vocabulary.

## Step 1: Pick the format

Read `references/routing.md` if the choice is not obvious. Short version:

| Content                                   | Format                    |
|-------------------------------------------|---------------------------|
| Explanation, procedure, decision, summary | STE prose                 |
| Structure, data flow, dependencies, states| Mermaid diagram + edges   |
| Trade-offs over parameters, "what if"     | HTML page with assumptions|

If the user named a format, use it.

## Step 2: Write the render file

Create `.ste/<short-slug>.md` in the working directory with exactly these sections,
in this order. Copy the shape from `examples/weight-tying.md`.

~~~markdown
# STE render: <title>

## Original
<the dense text, verbatim. If you are rendering your own answer, write the dense version first.>

## STE view
<the simplified text. For diagrams, put the ```mermaid block here plus 1-3 short sentences.>

## Edges
- <diagram mode only: one sentence per Mermaid edge, naming both ends by their label.
  Leave this whole section out in prose mode.>

## Preserved terms
- <every identifier, parameter name, error string, file path, version, and number
  that must appear unchanged in the STE view>

## Claims
```json
[{"id": "C1", "claim": "<one fact from the original>", "anchors": ["<exact token(s) that prove it survived>"]}]
```
~~~

How to write claims: one claim per fact a reader would act on. Each needs at least
one anchor: an exact string (identifier, number, or key phrase) that must appear in
the STE view. Pick anchors that can only be present if the fact survived. For
conditions, anchor the condition word with its object, e.g. `"unless"`, `"not guaranteed"`.

How to write the STE view: follow `references/writing-rules.md`. The ones that
matter most:

- Max 20 words per sentence in procedures (numbered steps), 25 in descriptions.
- Max 6 sentences per paragraph. One topic per paragraph.
- Active voice. Say who does what. In steps, use the imperative.
- No semicolons. Split the sentence.
- One instruction per step. Put the condition first: "If X, do Y."
- Keep every `if`, `unless`, `not`, `only`, `until`. These carry meaning.
- Keep identifiers exactly as written, in backticks.
- Use one term for one thing. Do not switch between synonyms.

**Soft mode ("80% STE").** If the user asks for softer or "80%" STE, or the
content is conceptual rather than procedural, run the checker with `--soft`. Style
limits become warnings. Fact retention stays an error.

## Step 3: Run the checker

```bash
python3 <this-skill-dir>/scripts/ste_check.py .ste/<slug>.md          # strict
python3 <this-skill-dir>/scripts/ste_check.py .ste/<slug>.md --soft   # 80% mode
```

`<this-skill-dir>` is the directory that contains this SKILL.md (usually
`~/.claude/skills/ste-render` or `.claude/skills/ste-render`).

- **Errors:** fix the STE view and run again. Up to 3 rounds.
- **fact-retention / preserved-term errors:** put the fact back. Do not "fix" them by
  deleting the claim or the term from the list. That defeats the check.
- **hedge warnings:** for each one, either restore the word or confirm the meaning
  survived in another form (e.g. "may call X" became "If ..., the agent calls X").
  Say which in your reply.
- **passive-voice warnings in descriptions:** allowed only if the agent is unknown.
  Otherwise rewrite.
- After 3 rounds with errors left, stop. Show the render and list the remaining errors.

## Step 4: Reply to the user

Show the STE view (or the diagram) first. Then, in one or two lines:

- the checker result, e.g. `ste_check: 0 errors, 1 warning (hedge 'may' -> resolved as condition)`
- the path to the render file, which holds the original and the claims

Do not paste the original again unless asked.

## HTML mode

Build a single self-contained HTML page. It must contain an element with
`id="assumptions"` holding a `<ul>` of the model's assumptions, visible on the page.
Prefer a page that lets the reader change one assumption and see what breaks.
Check it with:

```bash
python3 <this-skill-dir>/scripts/ste_check.py page.html
```

See `examples/kv-cache-sizing.html`.

## What this skill does not do

- It does not check the ASD-STE100 dictionary (about 900 approved words). That list
  is copyrighted and not bundled. So the output is "STE-style", not certified STE.
- Anchor checks are lexical. A fact can keep its anchor and still change meaning.
  The claims list makes that visible for review. It does not prove it away.
- It does not make video. For Manim/3b1b-style video, keep the script as an STE
  render first, then animate from it.
