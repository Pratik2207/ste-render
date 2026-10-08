# Choosing the output format

Karpathy's ladder goes: STE writing, then diagrams, then HTML, then video. Each
is easier to take in. Each also hides errors in a new place. Pick by the shape
of the content, not by what looks best.

## STE prose

Use for: explanations, procedures, decisions, incident summaries, code walkthroughs.

Where errors hide: dropped conditions and rounded numbers.
What protects you: claims with anchors, the hedge check.

Use strict mode for procedures (runbooks, setup steps). Use `--soft` for
conceptual explanations, where the full spec makes text stiff.

## Mermaid diagram

Use for: data flow, request paths, dependencies, state machines, architecture.
Use when the reader needs to see *what connects to what*.

Where errors hide: in missing arrows. A missing edge silently says "no
dependency". A reversed arrow looks as confident as a correct one.
What protects you: the `## Edges` section. One sentence per edge, naming both
ends. The checker fails if any edge has no sentence. A human can then read the
sentences in 20 seconds and spot the wrong one.

Rules:
- Use `flowchart` with simple edges (`-->`, `-.->`, `==>`, `---`). The checker
  does not parse `A -- text --> B` or `A & B --> C`. Use `A -->|text| B` and one
  edge per pair instead.
- Give every node a readable label: `API[Payments API]`, not `A`.
- Put conditions on edges as labels: `-->|if not cached|`.
- Keep it under about 15 nodes. Split bigger systems into two diagrams.

## HTML page

Use for: trade-offs across parameters, sizing, cost or latency estimates,
anything where the reader asks "what if I change X?".

Where errors hide: in code and layout. A polished page can be wrong in a way
that looks authoritative.
What protects you: a visible `#assumptions` list (checked), and a control that
changes one assumption so the reader sees its effect.

Rules:
- One self-contained file. No external requests except pinned CDN scripts if needed.
- Show the formula the page computes, in text, on the page.
- The page tests the page's model of the system, not the real system. Say so if
  the user will act on it.

## Video (not covered by the checker)

For a Manim / 3b1b-style explainer: write the narration script as an STE render
first and pass the checker. Then animate from the script. Keep the script and
captions, so the claims stay searchable.
