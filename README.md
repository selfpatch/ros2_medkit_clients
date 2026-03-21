# ros2_medkit_clients

OpenAPI-generated client libraries for the [ros2_medkit gateway](https://github.com/selfpatch/ros2_medkit).

## Structure

| Path | Description |
|------|-------------|
| `spec/openapi.yaml` | OpenAPI 3.1.0 spec snapshot from gateway runtime |
| `clients/typescript/` | TypeScript client (`@selfpatch/ros2-medkit-client-ts`) |
| `clients/python/` | Python client (`ros2-medkit-client`) |
| `scripts/export-spec.sh` | Export spec from a running gateway |
| `scripts/generate.sh` | Generate client code from the spec |

## Spec Version

Current spec is from gateway **v0.4.0** - see `SPEC_VERSION` for exact version.

## Usage

### Export a fresh spec from a running gateway

```bash
# Start the gateway first (default: http://localhost:8080)
./scripts/export-spec.sh

# Or specify a custom URL
GATEWAY_URL=http://192.168.1.10:8080 ./scripts/export-spec.sh
```

### Generate client code

```bash
./scripts/generate.sh
```

### Validate the spec

```bash
npx @stoplight/spectral-cli@6.14.2 lint spec/openapi.yaml
```

## License

Apache 2.0 - see [LICENSE](LICENSE).
