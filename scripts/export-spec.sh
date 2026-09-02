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

# Convert JSON to YAML (portable - no yq dependency).
#
# `servers` carries whichever port the exporting gateway happened to be bound to,
# which is a property of that one run and not of the API, so it is pinned to the
# gateway's documented default. Nothing depends on the value - neither generated
# client reads `servers`, both take the base URL from their caller - so the point
# is only that the committed snapshot describes the API rather than a session.
raw_spec=$(mktemp)
trap 'rm -f "$raw_spec"' EXIT
printf '%s' "$json_spec" > "$raw_spec"

python3 - "$raw_spec" "$SPEC_OUTPUT" <<'PYCONV'
import json
import sys
from urllib.parse import urlsplit, urlunsplit

import yaml

DEFAULT_PORT = 8080
in_path, out_path = sys.argv[1], sys.argv[2]
with open(in_path) as handle:
    spec = json.load(handle)

for server in spec.get("servers", []):
    parts = urlsplit(server.get("url", ""))
    if parts.scheme not in ("http", "https") or parts.port in (None, DEFAULT_PORT):
        continue
    # Only the port is replaced, by cutting it off the authority rather than
    # rebuilding one. `parts.hostname` is lowercased, has no userinfo and has had
    # the brackets stripped off an IPv6 literal, so a netloc built back up from it
    # loses whatever the gateway actually reported.
    authority = parts.netloc.rsplit(":", 1)[0]
    server["url"] = urlunsplit(parts._replace(netloc=f"{authority}:{DEFAULT_PORT}"))
    print(f"Normalized server URL port {parts.port} -> {DEFAULT_PORT}", file=sys.stderr)

with open(out_path, "w") as handle:
    yaml.dump(spec, handle, default_flow_style=False, sort_keys=True)
PYCONV

# Extract gateway version from spec
gateway_version=$(echo "$json_spec" | jq -r '.info.version // "unknown"')
echo "$gateway_version" > "$REPO_ROOT/SPEC_VERSION"

echo "Spec exported: $SPEC_OUTPUT (gateway $gateway_version, OpenAPI $openapi_version)"
