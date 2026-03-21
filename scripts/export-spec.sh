#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"
SPEC_OUTPUT="$REPO_ROOT/spec/openapi.yaml"

echo "Exporting OpenAPI spec from $GATEWAY_URL/api/v1/docs ..."

# Fetch JSON spec from gateway
json_spec=$(curl -sf "$GATEWAY_URL/api/v1/docs")
if [ -z "$json_spec" ]; then
  echo "ERROR: Failed to fetch spec from $GATEWAY_URL/api/v1/docs" >&2
  echo "Is the gateway running?" >&2
  exit 1
fi

# Validate it looks like an OpenAPI spec
openapi_version=$(echo "$json_spec" | jq -r '.openapi // empty')
if [ -z "$openapi_version" ]; then
  echo "ERROR: Response does not contain an 'openapi' field - not a valid OpenAPI spec" >&2
  exit 1
fi

# Convert JSON to YAML
echo "$json_spec" | yq -y . > "$SPEC_OUTPUT"

# Extract gateway version from spec
gateway_version=$(echo "$json_spec" | jq -r '.info.version // "unknown"')
echo "$gateway_version" > "$REPO_ROOT/SPEC_VERSION"

echo "Spec exported: $SPEC_OUTPUT (gateway $gateway_version, OpenAPI $openapi_version)"
