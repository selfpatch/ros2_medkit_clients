import { describe, test, expect, vi, afterEach } from 'vitest';
import { createMedkitClient, normalizeBaseUrl, getTimeoutForPath, createTimeoutMiddleware } from '../src/client.js';

describe('normalizeBaseUrl', () => {
  test('adds http:// when no protocol', () => {
    expect(normalizeBaseUrl('localhost:8080')).toBe('http://localhost:8080/api/v1');
  });

  test('adds /api/v1 when missing', () => {
    expect(normalizeBaseUrl('http://localhost:8080')).toBe('http://localhost:8080/api/v1');
  });

  test('preserves existing /api/v1', () => {
    expect(normalizeBaseUrl('http://localhost:8080/api/v1')).toBe('http://localhost:8080/api/v1');
  });

  test('preserves https://', () => {
    expect(normalizeBaseUrl('https://gateway.example.com')).toBe('https://gateway.example.com/api/v1');
  });

  test('handles trailing slash', () => {
    expect(normalizeBaseUrl('http://localhost:8080/')).toBe('http://localhost:8080/api/v1');
  });

  test('handles /api/v1/', () => {
    expect(normalizeBaseUrl('http://localhost:8080/api/v1/')).toBe('http://localhost:8080/api/v1');
  });

  test('handles ip address with port', () => {
    expect(normalizeBaseUrl('192.168.1.10:8080')).toBe('http://192.168.1.10:8080/api/v1');
  });
});

describe('getTimeoutForPath', () => {
  const config = { default: 10_000, operations: 30_000, downloads: 300_000 };

  test('returns default timeout for regular paths', () => {
    expect(getTimeoutForPath('/api/v1/apps', config)).toBe(10_000);
    expect(getTimeoutForPath('/api/v1/components/lidar/data', config)).toBe(10_000);
  });

  test('returns operations timeout for execution paths', () => {
    expect(getTimeoutForPath('/api/v1/apps/node1/operations/restart/executions', config)).toBe(30_000);
  });

  test('returns downloads timeout for bulk-data download paths', () => {
    expect(getTimeoutForPath('/api/v1/apps/node1/bulk-data/cat1/file1/download', config)).toBe(300_000);
  });

  test('uses defaults when config is empty', () => {
    expect(getTimeoutForPath('/api/v1/apps', {})).toBe(10_000);
  });
});

describe('createTimeoutMiddleware', () => {
  test('aborts request after timeout', async () => {
    const middleware = createTimeoutMiddleware({ default: 50 });

    const request = new Request('http://localhost/api/v1/apps');
    const result = await middleware.onRequest!({
      request,
      schemaPath: '/apps',
      params: {},
      id: 'test',
      options: {} as never,
    });

    // The returned request should have an abort signal
    expect(result).toBeInstanceOf(Request);
    const newRequest = result as Request;
    expect(newRequest.signal).toBeDefined();
    expect(newRequest.signal.aborted).toBe(false);

    // Wait for timeout to fire
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(newRequest.signal.aborted).toBe(true);
  });

  test('clears timer on response', async () => {
    const middleware = createTimeoutMiddleware({ default: 5000 });

    const request = new Request('http://localhost/api/v1/apps');
    const newRequest = (await middleware.onRequest!({
      request,
      schemaPath: '/apps',
      params: {},
      id: 'test',
      options: {} as never,
    })) as Request;

    // Simulate response arriving quickly
    await middleware.onResponse!({
      request: newRequest,
      response: new Response('ok'),
      schemaPath: '/apps',
      params: {},
      id: 'test',
      options: {} as never,
    });

    // After timer would have fired, signal should NOT be aborted
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(newRequest.signal.aborted).toBe(false);
  });

  test('uses operations timeout for execution paths', async () => {
    const middleware = createTimeoutMiddleware({ default: 50, operations: 5000 });

    const request = new Request('http://localhost/api/v1/apps/node1/operations/restart/executions');
    const newRequest = (await middleware.onRequest!({
      request,
      schemaPath: '/apps/{app_id}/operations/{operation_id}/executions',
      params: {},
      id: 'test',
      options: {} as never,
    })) as Request;

    // Default timeout (50ms) should NOT abort - operations timeout is 5000ms
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(newRequest.signal.aborted).toBe(false);
  });
});

describe('createMedkitClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test('creates a client with normalized URL', () => {
    const client = createMedkitClient({ baseUrl: 'localhost:8080' });
    expect(client).toBeDefined();
    expect(client.GET).toBeTypeOf('function');
    expect(client.POST).toBeTypeOf('function');
    expect(client.streams).toBeDefined();
  });

  test('sets Authorization header when auth provided', async () => {
    let capturedHeaders: Headers | undefined;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      // openapi-fetch passes a Request object as `input`; headers live on it
      if (input instanceof Request) {
        capturedHeaders = input.headers;
      }
      return new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }));

    const client = createMedkitClient({
      baseUrl: 'localhost:8080',
      auth: { token: 'test-jwt-token' },
    });

    await client.GET('/apps');
    expect(capturedHeaders?.get('Authorization')).toBe('Bearer test-jwt-token');
  });

  test('uses custom fetch when provided', async () => {
    const mockFetch = vi.fn(async () =>
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const client = createMedkitClient({
      baseUrl: 'localhost:8080',
      fetch: mockFetch,
    });

    await client.GET('/apps');
    expect(mockFetch).toHaveBeenCalledOnce();
  });

  test('error middleware transforms 4xx into MedkitError', async () => {
    const mockFetch = vi.fn(async () =>
      new Response(JSON.stringify({ error_code: 'entity-not-found', message: 'App x not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const client = createMedkitClient({
      baseUrl: 'localhost:8080',
      fetch: mockFetch,
    });

    const { error } = await client.GET('/apps/{app_id}', {
      params: { path: { app_id: 'x' } },
    });

    expect(error).toBeDefined();
    // The error body has been transformed by errorMiddleware
    const errorBody = error as unknown as Record<string, unknown>;
    expect(errorBody.code).toBe('entity-not-found');
    expect(errorBody.status).toBe(404);
  });
});
