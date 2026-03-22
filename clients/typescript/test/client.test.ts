import { describe, test, expect, vi, afterEach } from 'vitest';
import { createMedkitClient, normalizeBaseUrl, getTimeoutForPath } from '../src/client.js';

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
});
