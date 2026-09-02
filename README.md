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

Current spec is from gateway **v0.7.0** - see `SPEC_VERSION` for exact version.

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

## TypeScript Client

### Setup

```bash
npm install @selfpatch/ros2-medkit-client-ts openapi-fetch
```

### Usage

```typescript
import { createMedkitClient } from '@selfpatch/ros2-medkit-client-ts';

// Create a client (URL is normalized - adds http:// and /api/v1 if missing)
const client = createMedkitClient({ baseUrl: 'localhost:8080' });

// CRUD operations - fully typed from the OpenAPI spec
const { data, error } = await client.GET('/apps');
if (error) {
  console.error(error.code, error.message); // MedkitError
}

// SSE streaming - faults, triggers, subscriptions
for await (const event of client.streams.faults()) {
  console.log(event.data);
}

// With authentication
const authedClient = createMedkitClient({
  baseUrl: 'localhost:8080',
  auth: { token: 'your-jwt-token' },
});
```

See `clients/typescript/` for the full source and API.

## Python Client

### Setup

The wheel is attached to a GitHub release, not published to a package index:

```bash
pip install https://github.com/selfpatch/ros2_medkit_clients/releases/download/py-v0.7.0/ros2_medkit_client-0.7.0-py3-none-any.whl
```

### Usage

```python
from ros2_medkit_client import MedkitClient, MedkitError
from ros2_medkit_client.api.discovery import list_apps

async with MedkitClient(base_url="localhost:8080") as client:
    # Option 1: call() bridges errors into MedkitError exceptions
    apps = await client.call(list_apps.asyncio)

    # Option 2: raw generated API (returns SuccessType | GenericError | None)
    result = await list_apps.asyncio(client=client.http)

    # SSE streaming
    async for event in client.streams.faults():
        print(event.data)

    # Error handling with call()
    try:
        apps = await client.call(list_apps.asyncio)
    except MedkitError as e:
        print(e.code, e.message)
```

See `clients/python/` for the full source and API.

## License

Apache 2.0 - see [LICENSE](LICENSE).
