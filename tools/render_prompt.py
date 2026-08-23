#!/usr/bin/env python3
"""
Render the master YAML into the system prompt embedded in index.html.

The YAML is the authored source of truth for the engine's theory. The browser
cannot parse YAML without a dependency and cannot fetch a sibling file over
file://, so the rendered prompt is embedded in index.html between markers.
This script regenerates it, keeping the two from drifting.

    python tools/render_prompt.py            # regenerate and inject
    python tools/render_prompt.py --check    # verify sync, exit 1 if stale

Injects into index.html:
    /* SYSTEM_PROMPT:BEGIN */ `...` /* SYSTEM_PROMPT:END */
    /* SCHEMA:BEGIN */ {...} /* SCHEMA:END */

Also writes prompts/system-prompt.generated.md so the prompt can be read,
diffed, and reviewed as plain text.

Requires: pyyaml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required:  pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "prompts" / "rhetorical-dynamics-studio.yaml"
SCHEMA_PATH = ROOT / "schema" / "rhetorical-transformation.schema.json"
HTML_PATH = ROOT / "index.html"
PROMPT_MD_PATH = ROOT / "prompts" / "system-prompt.generated.md"


# ─────────────────────────── rendering helpers ───────────────────────────

def clean(text) -> str:
    """Collapse YAML folded-block whitespace into a single flowing paragraph."""
    return " ".join(str(text).split())


def bullets(items, indent: str = "") -> str:
    return "\n".join(f"{indent}- {clean(i)}" for i in items)


def render_prompt(doc: dict) -> str:
    si = doc["system_instructions"]
    meta = doc.get("metadata", {})
    out: list[str] = []
    add = out.append

    add("# RHETORICAL TRANSFORMATION ENGINE")
    add("")
    add(clean(si["role"]))
    add("")

    # ── Prime directives
    add("## PRIME DIRECTIVES")
    add("")
    add("These override every other instruction below.")
    add("")
    for pd in si["prime_directives"]:
        add(f"**{pd['id']} — {pd['name']}.** {clean(pd['rule'])}")
        add("")

    # ── Grade bands
    add("## DIMENSION 1 — TARGET GRADE BAND")
    add("")
    for key, b in si["transformation_matrix"]["grade_bands"].items():
        fk_lo, fk_hi = b["target_fk_range"]
        msl_lo, msl_hi = b["mean_sentence_length_words"]
        add(f"### {key}  (schema label: \"{b['schema_label']}\")")
        add(f"- Flesch-Kincaid target: {fk_lo}–{fk_hi}")
        add(f"- Mean sentence length: {msl_lo}–{msl_hi} words")
        add(f"- Lexicon: {clean(b['target_lexicon'])}")
        add(f"- Syntax: {clean(b['syntactic_complexity'])}")
        add(f"- Cohesion: {clean(b['cohesion_requirement'])}")
        add(f"- Scaffolding: {clean(b['scaffolding'])}")
        add(f"- Cognitive demand: {b['cognitive_demand']}")
        add(f"- Developmental verbs available: {', '.join(b['developmental_verbs'])}")
        add("")

    # ── Stances
    add("## DIMENSION 2 — PRAGMATIC STANCE")
    add("")
    for key, s in si["transformation_matrix"]["pragmatic_stances"].items():
        add(f"### {key}")
        add(f"- Objective: {clean(s['objective'])}")
        add(f"- Rhetorical focus: {clean(s['rhetorical_focus'])}")
        add("- Operational rules:")
        add(bullets(s["operational_rules"], indent="  "))
        add(f"- Signature syntax: {' | '.join(s['signature_syntax'])}")
        add("")

    # ── Moves
    add("## THE FIVE RHETORICAL MOVES")
    add("")
    for m in si["rhetorical_moves"]:
        add(f"### {m['id']} — {m['name']}  [{m['type']}]")
        add(f"*Source: {m['origin']}*")
        add("")
        add(f"**Effect.** {clean(m['effect'])}")
        add("")
        add(f"**Rule.** {clean(m['rule'])}")
        add("")
        if "templates" in m:
            add("**Templates.**")
            for name, tpl in m["templates"].items():
                add(f"- `{name}`: {clean(tpl)}")
            add("")
        if "progression" in m:
            add("**Voice progression.**")
            for name, ex in m["progression"].items():
                add(f"- `{name}`: {clean(ex)}")
            add("")
        if "stance_mapping" in m:
            add("**Stance mapping.**")
            for name, val in m["stance_mapping"].items():
                add(f"- `{name}` → {clean(val)}")
            add("")
        if "grade_band_realization" in m:
            add("**Realization by band.**")
            for name, val in m["grade_band_realization"].items():
                add(f"- {name}: {clean(val)}")
            add("")
        if "worked_example" in m:
            add("**Worked example.**")
            for name, val in m["worked_example"].items():
                add(f"- {name}: {clean(val)}")
            add("")
        for extra_key, label in (
            ("anti_pattern", "Anti-pattern"),
            ("quality_gate", "Quality gate"),
        ):
            if extra_key in m:
                add(f"**{label}.** {clean(m[extra_key])}")
                add("")

    # ── Vocabulary
    vd = si["vocabulary_doctrine"]
    add("## VOCABULARY DOCTRINE")
    add("")
    add("**Tier definitions.**")
    for name, definition in vd["tier_definitions"].items():
        add(f"- {name}: {clean(definition)}")
    add("")
    for r in vd["rules"]:
        add(f"### {r['id']} — {r['name']}")
        add(clean(r["rule"]))
        add("")
        if "progression" in r:
            add("**Introduction schedule.**")
            for grade, verbs in r["progression"].items():
                add(f"- {grade}: {', '.join(verbs)}")
            add("")
        if "task_scaling" in r:
            add("**Task scaling.**")
            for band, task in r["task_scaling"].items():
                add(f"- {band}: {clean(task)}")
            add("")
        if "example" in r:
            add("**Example.**")
            for name, val in r["example"].items():
                add(f"- {name}: {clean(val)}")
            add("")
        if "enforcement" in r:
            add(f"**Enforcement.** {clean(r['enforcement'])}")
            add("")

    # ── Toggles
    add("## SCAFFOLDING TOGGLES")
    add("")
    add("The client supplies these as booleans. Honor them exactly.")
    add("")
    for key, t in si["scaffolding_toggles"].items():
        add(f"### {key}  (`{t['flag']}`)")
        add(f"- When true: {clean(t['when_true'])}")
        add(f"- When false: {clean(t['when_false'])}")
        add("")

    # ── Protocol
    ep = si["execution_protocol"]
    add("## EXECUTION PROTOCOL")
    add("")
    add("**Input payload.**")
    add(bullets(ep["input_payload"]))
    add("")
    add("**Work in this order.**")
    for s in ep["ordered_steps"]:
        add(f"{s['step']}. {clean(s['action'])}")
    add("")
    add("**Self-check before emitting.**")
    add(bullets(ep["self_check_before_emitting"]))
    add("")

    oc = ep["output_contract"]
    add("## OUTPUT CONTRACT")
    add("")
    add(f"Format: {oc['format']}. Strict schema conformance is required.")
    add("")
    add(bullets(oc["rules"]))
    add("")

    add("## EDGE CASES")
    add("")
    for name, rule in si["refusal_and_edge_cases"].items():
        add(f"- **{name}**: {clean(rule)}")
    add("")

    if meta.get("theoretical_frameworks"):
        add("## SOURCE FRAMEWORKS")
        add("")
        for f in meta["theoretical_frameworks"]:
            add(f"- **{f['citation']}** — {clean(f['contributes'])}")
        add("")

    return "\n".join(out).rstrip() + "\n"


def js_template_literal(text: str) -> str:
    """Escape text for embedding inside a JavaScript backtick template literal."""
    return (
        text.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("${", "\\${")
    )


def inject(html: str, marker: str, payload: str) -> str:
    pattern = re.compile(
        r"(/\* " + re.escape(marker) + r":BEGIN \*/).*?(/\* " + re.escape(marker) + r":END \*/)",
        re.DOTALL,
    )
    if not pattern.search(html):
        sys.exit(f"marker {marker} not found in index.html")
    return pattern.sub(lambda m: m.group(1) + " " + payload + " " + m.group(2), html)


# ─────────────────────────────── entry point ───────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify index.html is in sync; exit 1 if stale")
    args = parser.parse_args()

    doc = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    prompt = render_prompt(doc)
    html = HTML_PATH.read_text(encoding="utf-8")

    updated = inject(html, "SYSTEM_PROMPT", "`" + js_template_literal(prompt) + "`")
    updated = inject(updated, "SCHEMA", json.dumps(schema, indent=2, ensure_ascii=False))

    if args.check:
        if updated != html or PROMPT_MD_PATH.read_text(encoding="utf-8") != prompt:
            print("STALE — index.html does not match the YAML. Run: python tools/render_prompt.py")
            return 1
        print("in sync")
        return 0

    HTML_PATH.write_text(updated, encoding="utf-8")
    PROMPT_MD_PATH.write_text(prompt, encoding="utf-8")

    words = len(prompt.split())
    print(f"rendered system prompt: {len(prompt):,} chars / ~{words:,} words")
    print(f"embedded schema:        {len(json.dumps(schema)):,} chars")
    print(f"wrote {HTML_PATH.relative_to(ROOT)} and {PROMPT_MD_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
