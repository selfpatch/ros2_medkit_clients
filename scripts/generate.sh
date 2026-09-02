#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SPEC_FILE="$REPO_ROOT/spec/openapi.yaml"

if [ ! -f "$SPEC_FILE" ]; then
  echo "ERROR: Spec not found at $SPEC_FILE" >&2
  echo "Run ./scripts/export-spec.sh first" >&2
  exit 1
fi

# Check required tools
for cmd in npx pipx; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: $cmd not found. Install it first." >&2
    exit 1
  fi
done

echo "=== Generating clients from $SPEC_FILE ==="

# --- TypeScript ---
echo ""
echo "--- TypeScript client ---"
TS_DIR="$REPO_ROOT/clients/typescript"
TS_GEN_DIR="$TS_DIR/generated"
mkdir -p "$TS_GEN_DIR"

npx openapi-typescript@7.13.0 "$SPEC_FILE" -o "$TS_GEN_DIR/schema.d.ts"
echo "TypeScript types generated: $TS_GEN_DIR/schema.d.ts"

# --- Python ---
echo ""
echo "--- Python client ---"
PY_DIR="$REPO_ROOT/clients/python"
PY_GEN_DIR="$PY_DIR/generated"

# Ensure parent directory exists (not tracked in git)
mkdir -p "$PY_DIR"

# Remove previous generated output (openapi-python-client refuses to overwrite)
if [ -d "$PY_GEN_DIR" ]; then
  rm -rf "$PY_GEN_DIR"
fi

# Use openapi-python-client to generate async httpx + attrs client
# --meta none skips pyproject.toml generation (we manage that separately)
pipx run openapi-python-client==0.28.3 generate \
  --path "$SPEC_FILE" \
  --output-path "$PY_GEN_DIR" \
  --meta none

echo "Python client generated: $PY_GEN_DIR/"

# An endpoint that accepts one schema under two content types gets a body typed
# `Schema | Unset = UNSET`, but the emitted import line only brings in the UNSET
# sentinel, not the Unset class the annotation names. Importing such a module
# raises NameError before any request is made. `/auth/authorize` and
# `/auth/token` are in that shape, because RFC 6749 requires a token endpoint to
# accept application/x-www-form-urlencoded beside application/json.
# openapi-python-client 0.29.1 is the newest release and still emits it; the
# content_type_overrides setting collapses the duplicated union member but does
# not add the import.
python3 - "$PY_GEN_DIR" <<'PYFIX'
import pathlib
import re
import sys

gen_dir = pathlib.Path(sys.argv[1])
uses_unset = re.compile(r"(?<![A-Za-z0-9_.])Unset(?![A-Za-z0-9_])")
import_line = re.compile(r"^from (\.+)types import (.+)$", re.MULTILINE)
patched = []

for path in sorted(gen_dir.rglob("*.py")):
    source = path.read_text()
    match = import_line.search(source)
    if not match:
        continue
    names = [n.strip() for n in match.group(2).split(",")]
    if "Unset" in names:
        continue
    body = source[: match.start()] + source[match.end() :]
    if not uses_unset.search(body):
        continue
    # Appended rather than re-sorted: the generator already writes the names in
    # the order isort wants, and sorting them again moves UNSET behind Response.
    names.append("Unset")
    replacement = f"from {match.group(1)}types import {', '.join(names)}"
    path.write_text(source[: match.start()] + replacement + source[match.end() :])
    patched.append(path.relative_to(gen_dir))

for path in patched:
    print(f"Added the missing Unset import to {path}")
PYFIX

echo ""
echo "=== Generation complete ==="
