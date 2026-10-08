# Writing rules for the STE view

This is a working summary in our own words. It is **not** the ASD-STE100 text.
The authoritative source is ASD-STE100 Issue 9 (15 January 2025): 53 writing
rules in nine sections, plus a dictionary of about 900 approved words. Request a
copy from the official downloads page: https://www.asd-ste100.org/STE_downloads.html
The standard is free to obtain, but ASD holds the copyright, so this repo does
not bundle the rules text or the dictionary.

Rules marked **[checked]** are enforced by `scripts/ste_check.py`. The rest are
guidance for the model. A human or a future linter must check them.

## Words

- Use one word for one meaning. Use one term for one thing, every time. **[guidance]**
- Use a word only as one part of speech. Example from the standard: TEST is
  approved as a noun, not a verb. Write "do a test of the API", not "test the API". **[guidance]**
- APPROXIMATELY is approved. ABOUT is approved only as a preposition meaning
  "concerned with". Several AI-made STE cheat sheets get this backwards. **[guidance]**
- Technical nouns and technical verbs (names of parts, tools, functions,
  identifiers) are allowed. Keep identifiers exactly as written. **[checked via Preserved terms]**
- Prefer short, common words. The house list of wordy phrases in the checker
  ("in order to", "prior to", "utilize", ...) is ours, not the ASD dictionary. **[checked, warning]**

## Multi-word nouns

- Max three words in a noun cluster. Break longer ones with "of", "for", or a
  short clause: "the timeout of the retry policy", not "retry policy timeout value". **[guidance]**

## Verbs

- Use simple verb forms: infinitive, imperative, simple present, simple past,
  future, and the past participle used as an adjective. **[guidance]**
- Active voice. In procedures, always. **[checked: error in steps]**
- In descriptions, passive voice only when the agent is unknown. **[checked: warning]**

## Sentences and paragraphs

- Procedural sentence (numbered step): max 20 words. **[checked]**
- Descriptive sentence: max 25 words. **[checked]**
- Paragraph: max 6 sentences, one topic. **[checked: count]**
- One instruction per step, unless two actions happen at the same time. **[guidance]**
- Put the condition first: "If the cache is cold, warm it before the load test." **[guidance]**
- Start a paragraph with its topic sentence. **[guidance]**

## Punctuation

- No semicolons. **[checked]**

## Additions in this skill (not part of STE)

These protect meaning during simplification. They come from known failure modes
of AI simplification, where a cleaner sentence becomes a stronger claim.

- Keep every `if`, `unless`, `not`, `only`, `until`, `may`, `except`. **[checked: warning]**
- Every fact a reader would act on becomes a claim with an anchor. **[checked: error]**
- Keep numbers with their units and their precision. Do not round 38.6M to "about 40M". **[checked via anchors]**
- If the original says something is unverified, the STE view must say so too. **[checked via hedges]**
