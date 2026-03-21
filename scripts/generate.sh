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

echo "=== Generating clients from $SPEC_FILE ==="

# --- TypeScript ---
echo ""
echo "--- TypeScript client ---"
TS_DIR="$REPO_ROOT/clients/typescript"
TS_GEN_DIR="$TS_DIR/generated"
mkdir -p "$TS_GEN_DIR"

npx openapi-typescript "$SPEC_FILE" -o "$TS_GEN_DIR/schema.d.ts"
echo "TypeScript types generated: $TS_GEN_DIR/schema.d.ts"

# --- Python ---
echo ""
echo "--- Python client ---"
PY_DIR="$REPO_ROOT/clients/python"
PY_GEN_DIR="$PY_DIR/generated"

# Remove previous generated output (openapi-python-client refuses to overwrite)
if [ -d "$PY_GEN_DIR" ]; then
  rm -rf "$PY_GEN_DIR"
fi

# Use openapi-python-client to generate async httpx + Pydantic client
# --meta none skips pyproject.toml generation (we manage that separately)
pipx run openapi-python-client generate \
  --path "$SPEC_FILE" \
  --output-path "$PY_GEN_DIR" \
  --meta none

echo "Python client generated: $PY_GEN_DIR/"

echo ""
echo "=== Generation complete ==="
