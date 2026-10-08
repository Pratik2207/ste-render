# ste-render

A Claude Code skill that turns dense LLM output into something a human can read
fast: ASD-STE100-style English, Mermaid diagrams, or interactive HTML. Then it
**checks the result outside the model**, so facts, identifiers, numbers and
conditions don't silently disappear.

```
$ python3 scripts/ste_check.py examples/weight-tying.md
0 error(s), 0 warning(s) [strict]. Vocabulary is not checked (ASD dictionary not bundled).
```

## Why this exists

On 2 Oct 2026, Andrej Karpathy [posted](https://x.com/karpathy/status/2105819303471976479)
a ladder of formats for understanding model output: ask for ASD-STE100
(Simplified Technical English, built for aircraft maintenance manuals), then
diagrams, then HTML, then video. He sometimes asks for "80% of the way to
ASD-STE100" because the spec is strict.

Many STE prompt skills already exist. They share three problems:

1. **Simplification drops facts.** In one small informal test, a strict
   ASD-STE100 prompt made Claude mention 46.8% fewer scored facts in code
   explanations. Readable text that lost a condition is worse than dense text.
2. **"Compliance" is self-reported.** The model says it followed the rules. It
   often didn't. ASD's own 2026 white paper warns that plausibility is not
   verified compliance.
3. **AI-built word tables are wrong.** Several, including the cheat sheet in the
   original post, mark APPROXIMATELY as not approved. The standard approves it.

This skill takes a different approach: **the model writes, a deterministic
checker decides.**

## What the checker verifies

| Check            | What it catches                                                  | Level |
|------------------|------------------------------------------------------------------|-------|
| fact-retention   | A claim from the original whose anchor is missing from the STE view | error |
| preserved-term   | An identifier, number or error string that changed or vanished   | error |
| hedge            | `if` / `unless` / `not` / `only` / `may` ... that got dropped    | warning |
| sentence-length  | > 20 words in a numbered step, > 25 in a description             | error (warning in `--soft`) |
| paragraph-length | > 6 sentences in a paragraph                                     | error (warning in `--soft`) |
| semicolon        | Any `;` outside code                                             | error (warning in `--soft`) |
| passive-voice    | Passive in steps (error) or descriptions (warning)               | heuristic |
| wordy            | "in order to", "prior to", "utilize" ... (house list)            | warning |
| diagram-edges    | A Mermaid edge with no matching sentence in `## Edges`           | error |
| html-assumptions | An HTML page without a visible `#assumptions` list               | error |

Code blocks and inline code are excluded from style checks.

`--soft` is the "80% STE" mode: style becomes advisory. **Fact retention stays
an error in every mode.** That is the point of the tool.

## Install

Personal (all projects):

```bash
git clone https://github.com/<you>/ste-render ~/.claude/skills/ste-render
```

One project:

```bash
git clone https://github.com/<you>/ste-render .claude/skills/ste-render
```

Needs Python 3.9+. No dependencies. Restart Claude Code, then ask something like
"explain this in STE", "80% STE version please", or "diagram this flow".

## How a render looks

Each render is one Markdown file in `.ste/` with fixed sections:

```
## Original         the dense text, verbatim
## STE view         the simplified text (or a ```mermaid block)
## Edges            diagram mode: one sentence per edge
## Preserved terms  identifiers and numbers that must survive unchanged
## Claims           JSON list: {id, claim, anchors[]}
```

See [`examples/weight-tying.md`](examples/weight-tying.md) (prose),
[`examples/voice-agent-pipeline.md`](examples/voice-agent-pipeline.md) (diagram), and
[`examples/kv-cache-sizing.html`](examples/kv-cache-sizing.html) (HTML).

The diagram example shows one warning on purpose: `may` in the original became
an `if` condition in the STE view. The meaning survived, and the warning makes a
human confirm it. That is the intended workflow.

## Use the checker directly

```bash
python3 scripts/ste_check.py path/to/render.md            # strict
python3 scripts/ste_check.py path/to/render.md --soft     # 80% STE
python3 scripts/ste_check.py path/to/render.md --json     # for CI / other tools
python3 scripts/ste_check.py path/to/page.html            # HTML assumptions check
```

Exit codes: `0` no errors, `1` errors, `2` bad input (missing section, bad JSON).

## Optional: Vale

`vale/` holds a [Vale](https://vale.sh) style with the mechanical rules
(sentence length, semicolons, passive, wordy phrases) for editor integration.
Vale lints whole files, so use it on documents written fully in STE. For render
files, use the Python checker, which knows which section is which.

```bash
vale --config vale/.vale.ini docs/runbook.md
```

## Limitations (read these)

- **Vocabulary is not checked.** The ASD-STE100 dictionary (about 900 approved
  words) is copyrighted and not bundled. Output is "STE-style", not certified STE.
  Request the standard from the [official downloads page](https://www.asd-ste100.org/STE_downloads.html).
- **Anchor checks are lexical.** A fact can keep its anchor and still change
  meaning. The claims list makes that easy to review. It does not prove it.
- **The model writes its own claims.** If it misses a fact when it extracts
  claims, the checker can't catch the loss. Review the claims list on anything
  you will act on.
- **Passive and hedge checks are heuristics.** Expect some false positives.
- **The Mermaid parser handles simple flowcharts.** It does not parse
  `A -- text --> B` or `A & B --> C`.

## Development

```bash
pip install pytest
python -m pytest -q
```

`references/writing-rules.md` is a paraphrase written for this repo, not the
ASD text. Each rule says whether the checker enforces it.

## Credits

- Format ladder: Andrej Karpathy, post on X, 2 Oct 2026.
- ASD-STE100 is maintained by ASD (AeroSpace, Security and Defence Industries
  Association of Europe). This project is not affiliated with ASD.

## License

MIT. See [LICENSE](LICENSE).
