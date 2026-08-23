#!/usr/bin/env python3
"""
Validate that every Demo Mode response in index.html conforms to the schema.

Demo Mode exists so the app can be shown without an API key, which makes it a
liability: a curated response that quietly diverges from the schema would
misrepresent the contract the live path actually enforces. This script proves
they agree.

It also checks that the schema embedded in index.html is byte-identical to
schema/rhetorical-transformation.schema.json, and that the schema is
strict-mode clean (every object sets additionalProperties:false and lists all
of its properties in required) so it is accepted by both Anthropic's
output_config.format and OpenAI's strict json_schema.

    python tools/validate_demo.py

Requires: node (to evaluate the embedded JavaScript), pyyaml, jsonschema
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from jsonschema import Draft7Validator
except ImportError:
    sys.exit("jsonschema is required:  pip install jsonschema")

ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = ROOT / "index.html"
SCHEMA_PATH = ROOT / "schema" / "rhetorical-transformation.schema.json"

# Minimal DOM/lucide stubs: the app script defines everything at module scope
# and only touches the DOM inside handlers, so stubbing these three is enough
# to evaluate it in node and read the data structures back out.
HARNESS = """
globalThis.document = {
  addEventListener: () => {},
  querySelector: () => null,
  querySelectorAll: () => [],
  createElement: () => ({ classList: { add(){}, toggle(){} }, click(){}, remove(){} }),
  body: { appendChild: () => {} }
};
globalThis.lucide = { createIcons: () => {} };

__APP_SOURCE__

const sources = {};
for (const [key, preset] of Object.entries(PRESETS)) sources[key] = preset.text;

const generic = buildGenericDemo(
  "Photosynthesis converts light energy into chemical energy. Plants use this energy to build sugars from carbon dioxide and water.",
  "middle_school_6_8", "direct_instruction",
  { stems: true, vocab: true, syntax: false }
);

process.stdout.write(JSON.stringify({
  curated: DEMO_RESPONSES,
  generic: generic,
  schema: RESPONSE_SCHEMA,
  presets: sources,
  promptChars: SYSTEM_PROMPT.length
}));
"""


def extract_app_script(html: str) -> str:
    scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    if not scripts:
        sys.exit("no inline <script> found in index.html")
    return scripts[-1]


def strict_mode_violations(node, path="root", found=None):
    """Every object must set additionalProperties:false and require all keys."""
    if found is None:
        found = []
    if isinstance(node, dict):
        if node.get("type") == "object":
            if node.get("additionalProperties") is not False:
                found.append(f"{path}: missing additionalProperties:false")
            props = set(node.get("properties", {}))
            req = set(node.get("required", []))
            if props != req:
                missing = props - req
                extra = req - props
                detail = []
                if missing:
                    detail.append(f"not required: {sorted(missing)}")
                if extra:
                    detail.append(f"required but undefined: {sorted(extra)}")
                found.append(f"{path}: {'; '.join(detail)}")
        for k, v in node.items():
            strict_mode_violations(v, f"{path}.{k}", found)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            strict_mode_violations(v, f"{path}[{i}]", found)
    return found


def main() -> int:
    html = HTML_PATH.read_text(encoding="utf-8")
    app = extract_app_script(html)

    with tempfile.TemporaryDirectory() as tmp:
        harness = Path(tmp) / "harness.mjs"
        harness.write_text(HARNESS.replace("__APP_SOURCE__", app), encoding="utf-8")
        proc = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, encoding="utf-8"
        )
    if proc.returncode != 0:
        print(proc.stderr)
        sys.exit("failed to evaluate the app script in node")

    data = json.loads(proc.stdout)
    failures = 0

    # ── 1. embedded schema matches the file on disk
    on_disk = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if data["schema"] != on_disk:
        print("FAIL  embedded schema differs from schema/rhetorical-transformation.schema.json")
        print("      run: python tools/render_prompt.py")
        failures += 1
    else:
        print("PASS  embedded schema matches schema/rhetorical-transformation.schema.json")

    # ── 2. schema is strict-mode clean
    violations = strict_mode_violations(on_disk)
    if violations:
        print(f"FAIL  schema is not strict-mode clean ({len(violations)} issues)")
        for v in violations[:10]:
            print(f"      {v}")
        failures += 1
    else:
        print("PASS  schema is strict-mode clean (Anthropic + OpenAI compatible)")

    # ── 3. system prompt is present and substantial
    if data["promptChars"] < 5000:
        print(f"FAIL  embedded system prompt is only {data['promptChars']} chars - likely not rendered")
        print("      run: python tools/render_prompt.py")
        failures += 1
    else:
        print(f"PASS  embedded system prompt rendered ({data['promptChars']:,} chars)")

    # ── 4. every demo response validates
    validator = Draft7Validator(on_disk)
    responses = dict(data["curated"])
    responses["<generic fallback>"] = data["generic"]

    for name, resp in responses.items():
        errors = sorted(validator.iter_errors(resp), key=lambda e: list(e.path))
        if errors:
            print(f"FAIL  demo response '{name}' - {len(errors)} schema violation(s)")
            for e in errors[:5]:
                loc = "/".join(str(p) for p in e.path) or "(root)"
                print(f"      {loc}: {e.message}")
            failures += 1
        else:
            words = len(resp["transformed_text"].split())
            revs = len(resp["actionable_revisions"])
            print(f"PASS  demo response '{name}' - valid ({words} words, {revs} revisions)")

    # ── 5. every preset has a curated response
    for key in data["presets"]:
        if key not in data["curated"]:
            print(f"FAIL  preset '{key}' has no curated demo response")
            failures += 1

    print()
    if failures:
        print(f"{failures} check(s) failed")
        return 1
    print(f"all checks passed ({len(responses)} demo responses validated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
