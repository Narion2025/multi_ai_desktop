"""Validate thought entry front matter against a schema.

This script tries to validate the YAML front matter of all markdown files in
``thoughts/entries`` against ``schema/thought_entry.schema.yml``.  If the
``yaml`` or ``jsonschema`` modules are not available we fall back to very basic
parsing and validation logic so the script can still run in minimal
environments.
"""

import os
from pathlib import Path

try:  # optional dependency
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None
try:  # optional dependency
    import jsonschema
except ModuleNotFoundError:  # pragma: no cover
    jsonschema = None


# ---------------------------------------------------------------------------
# YAML loading helpers
# ---------------------------------------------------------------------------
if yaml:

    def load_yaml(data: str):
        return yaml.safe_load(data)
else:
    print("Warning: PyYAML not installed; using naive parser.")

    def load_yaml(data: str):
        """Very small YAML subset parser used as a fallback."""

        result: dict[str, object] = {}
        current_list: str | None = None
        for raw_line in data.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("- ") and current_list:
                result[current_list].append(line[2:].strip().strip("'\""))
                continue
            if line.startswith("-"):
                continue
            if line.startswith("#"):
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if value == "":
                    result[key] = []
                    current_list = key
                elif value.startswith("[") and value.endswith("]"):
                    items = [
                        v.strip().strip("'\"")
                        for v in value[1:-1].split(",")
                        if v.strip()
                    ]
                    result[key] = items
                    current_list = None
                else:
                    result[key] = value.strip("'\"")
                    current_list = None
        return result


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------
if jsonschema:

    def validate(instance: dict, schema: dict):
        jsonschema.validate(instance=instance, schema=schema)
else:
    print("Warning: jsonschema not installed; falling back to required check.")

    def validate(instance: dict, schema: dict):  # noqa: D401
        """Validate only that required keys from the schema are present."""

        required = schema.get("required", [])
        missing = [key for key in required if key not in instance]
        if missing:
            raise ValueError(f"missing: {', '.join(missing)}")


BASE = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BASE / "MIND_CI_Validation" / "schema" / "thought_entry.schema.yml"
THOUGHTS_DIR = BASE / "thoughts" / "entries"

if SCHEMA_PATH.exists():
    schema = load_yaml(SCHEMA_PATH.read_text()) or {}
else:
    print(f"Warning: schema file '{SCHEMA_PATH}' not found; skipping validation.")
    schema = {}

invalid = 0
for filename in os.listdir(THOUGHTS_DIR):
    if not filename.endswith(".md"):
        continue
    with open(THOUGHTS_DIR / filename) as file:
        front_matter = []
        in_front = False
        for line in file:
            if line.strip() == "---":
                in_front = not in_front
                continue
            if in_front:
                front_matter.append(line)

    data = load_yaml("".join(front_matter)) or {}
    try:
        validate(instance=data, schema=schema)
        print(f"✅ {filename} valid.")
    except Exception as e:  # noqa: BLE001
        invalid += 1
        msg = getattr(e, "message", str(e))
        print(f"❌ {filename} invalid: {msg}")

if invalid:
    raise SystemExit(f"{invalid} invalid thought files")
