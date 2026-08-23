# Rhetorical Dynamics Studio

### [→ Open the live demo](https://kaminczak.github.io/rhetorical-dynamics-studio/)

[![CI](https://github.com/Kaminczak/rhetorical-dynamics-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/Kaminczak/rhetorical-dynamics-studio/actions/workflows/ci.yml)
[![Pages](https://github.com/Kaminczak/rhetorical-dynamics-studio/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/Kaminczak/rhetorical-dynamics-studio/actions/workflows/deploy-pages.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**A prompt-engineering workbench that transforms instructional text across grade bands and rhetorical stances — and shows its linguistic reasoning for every change it makes.**

Paste a passage. Set a target grade band, a pragmatic stance, and the scaffolding you want. The engine rewrites the text and returns a structured diagnostic naming which rhetorical move, syntactic principle, or vocabulary rule licensed each decision.

The interesting part is not the rewriting. It is that **the rewriting is auditable** — every change traces to a named framework, and the trade-offs are surfaced rather than hidden.

```
index.html — open it. No build step, no dependencies, no key required.
```

---

## Why this exists

Most "reading level adjusters" do the same thing: they swap hard words for easy ones and shorten sentences. That fails the classroom for a reason worth naming.

Marilee Sprenger's work on Common Core vocabulary identifies the failure precisely. When you replace *contrast* with *find differences*, you have not made the concept accessible — you have denied the student exposure to the exact terminology they will meet on the assessment. **The word should stay. The scaffold around it should change.**

This project takes that principle and six others like it, drawn from rhetoric and applied linguistics, and encodes them as executable prompt constraints. The result is a system that can raise or lower register without diluting content, and can explain itself in the vocabulary of the field.

---

## The theoretical architecture

Seven sources, each contributing a specific mechanism rather than general inspiration.

| Framework | Source | What it contributes |
|---|---|---|
| **They Say / I Say** | Graff & Birkenstein | The "They Say" contextualizing move, concession-rebuttal pivots, preemptive naysayer integration |
| **Rhetorical Grammar** | Martha Kolln | Voice as a register dial; the Given-New cohesion contract |
| **Genre Analysis** | John Swales | CARS structural moves; discourse-community awareness |
| **Critical Vocabulary of the Common Core** | Marilee Sprenger (after Beck & McKeown) | Tier 1/2/3 classification, the developmental verb schedule, the recoding loop |
| **Encyclopedia of Rhetoric** | Thomas O. Sloane (ed.) | Aristotelian proofs, stasis theory, tropes and schemes |
| **Metaphors We Live By** | Lakoff & Johnson | Conceptual framing; structural metaphor selection for analogies |
| **80 Ways to Use ChatGPT in the Classroom** | Stan Skrabut | Dual-prompting audience constraints; human-in-the-loop validation |

### From theory to constraint

Three worked examples of how a book becomes a rule the model must obey.

**Kolln's Given-New contract** says readers expect a sentence to open on information they already hold and close on what is new. Violate it and prose becomes technically correct but exhausting. So the engine verifies cohesion sentence by sentence, and every repaired break is logged to `repaired_cohesive_breaks` — the diagnostic names the cognitive leap the source forced on the reader.

**Kolln also reframes the passive voice** as a register instrument rather than an error. Agentless passive constructs scientific objectivity; active voice assigns accountability. The engine therefore maps voice to stance — Formal Academic drives the passive ratio up deliberately, Direct Instruction drives it down — and must justify the setting in `stylistic_appropriateness` rather than defaulting to "avoid passive voice."

**Sprenger's no-dilution rule** becomes the hardest constraint in the system. Tier 2 and Tier 3 targets are never replaced by simpler synonyms. Every retained term must appear in `preserved_target_terms` paired with the strategy that made it reachable — appositive gloss, contextual definition, concrete analogy, or morphological cue. And because a vivid metaphor can be quietly false, every analogy passes a validation gate before it ships: if the image obscures the mechanics of the concept, it is rejected and rebuilt.

---

## How it works

```
prompts/rhetorical-dynamics-studio.yaml     ← the authored source of truth
                │
                │  tools/render_prompt.py
                ▼
index.html      ← SYSTEM_PROMPT (22K chars) + RESPONSE_SCHEMA, embedded
                │
                ├── Demo Mode ────────────► curated, schema-valid responses
                ├── Anthropic ────────────► claude-opus-5, output_config.format
                └── OpenAI ───────────────► gpt-4o, strict json_schema
                                                   │
                schema/rhetorical-transformation.schema.json
                                  ▲
                                  └── one contract, all three paths
```

### The transformation matrix

Three independent dimensions the user controls:

**Grade band** — Elementary (3–5), Middle (6–8), High School (9–10), AP/College (11–12). Each carries a Flesch-Kincaid target range, a mean-sentence-length window, a syntactic profile, a cohesion requirement, and the set of academic verbs Sprenger schedules for that band.

**Pragmatic stance** — Socratic/Inquiry, Direct Instruction, Peer-to-Peer, Formal Academic. Each carries operational rules rather than adjectives. Socratic does not mean "ask some questions"; it means *convert at least half of all declarative assertions into questions a student could actually answer from the text, sequenced concrete to abstract, with the conclusion withheld* — and explicitly forbids the rhetorical question you answer yourself, which is direct instruction wearing a costume.

**Scaffolding toggles** — sentence stems, Tier 2/3 glossing, syntactic simplification. The third is deliberately constrained: it governs *syntax only*, and may never trigger vocabulary substitution, because that would violate the no-dilution rule.

### Single source of truth

The YAML is authored; the prompt embedded in `index.html` is generated from it. The browser cannot parse YAML without a dependency and cannot fetch a sibling file over `file://`, so the rendered prompt is injected between markers:

```bash
python tools/render_prompt.py
```

```bash
python tools/render_prompt.py --check
```

`--check` exits non-zero if `index.html` has drifted from the YAML, so CI catches a stale prompt.

### The response contract

Every path — mock, Anthropic, OpenAI — returns the same object, defined in [`schema/rhetorical-transformation.schema.json`](schema/rhetorical-transformation.schema.json):

| Field | Contents |
|---|---|
| `transformed_text` | Clean classroom prose. No bracketed move labels, no meta-commentary. |
| `transformation_summary` | Two to three sentences for a teacher: what changed and why. |
| `readability_analysis` | Source and output Flesch-Kincaid, band shift, and an explicit statement of whether any conceptual precision was traded away. |
| `rhetorical_stance_evaluation` | They Say backdrop, stance type, naysayer, concession-rebuttal pivots, CARS moves. |
| `syntax_and_sentence_variety` | Sentence-type distribution, active/passive ratio, nominalization density, Given-New alignment. |
| `vocabulary_analysis` | Tier counts, terms identified, recoding bridges, and preserved targets. |
| `scaffolding_applied` | Stems added, terms glossed, structural changes, Bloom/Webb demand level. |
| `actionable_revisions` | Span-level proposals a human can accept or reject. |

The schema is written in **strict mode** — every object sets `additionalProperties: false` and lists all properties in `required` — so one document satisfies both Anthropic's `output_config.format` and OpenAI's `response_format` with `strict: true`. No provider-specific variants to keep in sync.

---

## Running it

### Locally

Open `index.html` in a browser. That is the whole install. It boots into Demo Mode with a preset loaded.

For a local server (needed only if your browser restricts `file://`):

```bash
python -m http.server 8000
```

### Demo Mode

Runs with no API key. Three presets — 8th-grade history, AP environmental science, and elementary ELA — return curated responses written to demonstrate the full diagnostic. The **readability figures for arbitrary pasted text are computed in-browser**, not invented: Flesch-Kincaid, sentence segmentation, and syllable estimation all run locally, which is also why the source panel shows a real grade level before any model is called.

Demo Mode is verified against the schema rather than assumed to match it:

```bash
python tools/validate_demo.py
```

```
PASS  embedded schema matches schema/rhetorical-transformation.schema.json
PASS  schema is strict-mode clean (Anthropic + OpenAI compatible)
PASS  embedded system prompt rendered (22,241 chars)
PASS  demo response 'history_8th' - valid (199 words, 4 revisions)
PASS  demo response 'science_ap' - valid (215 words, 4 revisions)
PASS  demo response 'ela_ell' - valid (171 words, 4 revisions)
PASS  demo response '<generic fallback>' - valid (116 words, 1 revisions)
```

### Live mode

Click **Connect API**, choose a provider, paste a key.

- **Anthropic** — `claude-opus-5` with adaptive thinking, `effort: high`, and `output_config.format` carrying the JSON schema. Server-side refusal fallback is on by default; uncheck it if you would rather see a refusal than a silent model switch.
- **OpenAI** — `gpt-4o` with `response_format: json_schema` and `strict: true`.

> **Security.** This is a client-side demo. A key entered in the browser is held **in memory only** — never written to localStorage, never persisted — but it is still exposed to anything running in the page, and calling Anthropic from a browser requires the `anthropic-dangerous-direct-browser-access` header, which is named that way for a reason. Use a scoped, disposable key. **A production deployment must proxy through a server** so the key never reaches the client.

---

## Deploying

### GitHub Pages

Settings → Pages → Source: **GitHub Actions**. The included workflow publishes on every push to `main`.

### Vercel

```bash
vercel --prod
```

Zero configuration — it is a static file.

### Any static host

Upload `index.html`. It has no build step and no server-side dependency. The only runtime requests are the Tailwind and Lucide CDNs.

> For a real deployment, replace the Tailwind CDN with a compiled stylesheet. The CDN build ships the full JIT compiler to the browser, which is fine for a demo and wasteful in production.

---

## Repository layout

```
index.html                                  the application — single file, no build
prompts/
  rhetorical-dynamics-studio.yaml           master system prompt (authored)
  system-prompt.generated.md                rendered prompt, for diffing and review
schema/
  rhetorical-transformation.schema.json     the response contract
tools/
  render_prompt.py                          YAML → index.html injector (--check for CI)
  validate_demo.py                          schema-validates every demo response
docs/research/                              NotebookLM extractions the prompt was built from
  rhetorical-moves-and-stance.md
  vocabulary-and-cognitive-scaffolding.md
  diagnostic-breakdown-rationale.md
  text-evaluation-schema.source.json        original diagnostic-only schema
  original-project-brief.md
.github/workflows/                          CI (sync + schema checks) and Pages deploy
```

The source corpus itself — the books the research notes were extracted from — is **not** in this repository. Those are copyrighted texts held locally and excluded by `.gitignore`. What ships is the original synthesis in `docs/research/`.

---

## Development

```bash
pip install pyyaml jsonschema
```

Edit theory in the YAML, then regenerate and verify:

```bash
python tools/render_prompt.py && python tools/validate_demo.py
```

CI runs both on every push. `render_prompt.py --check` fails the build if `index.html` no longer matches the YAML, which is the failure mode this architecture is most exposed to.

---

## What this demonstrates

Built as a portfolio artifact for AI curriculum work, so it is worth stating plainly what it is meant to show.

**Prompt architecture as engineering, not phrasing.** A 22,000-character system prompt is generated from a versioned, structured source with a CI check against drift. Prompts are treated as artifacts with a build step and a test suite, because at this size they are.

**Domain expertise encoded as constraint.** The difference between this and a generic "rewrite for 5th grade" prompt is that the failure modes are anticipated. The no-dilution rule exists because synonym substitution is the default failure of reading-level tools. The metaphor validation gate exists because LLMs generate vivid, confident, false analogies for technical concepts. Twenty-five years of ELA classroom practice is in the guardrails, not the vocabulary.

**Structured output as a product decision.** Constraining the model to a strict schema is what makes the tool auditable. A teacher can see that a Tier 3 term was preserved, read the strategy that made it reachable, and disagree. The `actionable_revisions` array exists specifically so the model proposes rather than imposes.

**Honest failure surfaces.** `conceptual_accessibility_summary` is required to state whether precision was traded away. The system is built to admit when a concept could not be made reachable without becoming false — which is the only way a curriculum tool earns trust.

---

## License

MIT — see [LICENSE](LICENSE).

Theoretical frameworks belong to their authors and are cited, not reproduced. This repository contains original synthesis and implementation only.
