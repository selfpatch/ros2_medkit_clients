import { describe, test, expect, vi, afterEach } from 'vitest';
import { parseSseLine, SseStream } from '../src/sse.js';
import type { SseEvent } from '../src/types.js';

describe('parseSseLine', () => {
  test('parses event field', () => {
    const state = { event: 'message', data: '', id: undefined as string | undefined, retry: undefined as number | undefined };
    parseSseLine('event: fault', state);
    expect(state.event).toBe('fault');
  });

  test('parses data field', () => {
    const state = { event: 'message', data: '', id: undefined as string | undefined, retry: undefined as number | undefined };
    parseSseLine('data: {"id":"f1"}', state);
    expect(state.data).toBe('{"id":"f1"}');
  });

  test('concatenates multi-line data', () => {
    const state = { event: 'message', data: '', id: undefined as string | undefined, retry: undefined as number | undefined };
    parseSseLine('data: line1', state);
    parseSseLine('data: line2', state);
    expect(state.data).toBe('line1\nline2');
  });

  test('parses id field', () => {
    const state = { event: 'message', data: '', id: undefined as string | undefined, retry: undefined as number | undefined };
    parseSseLine('id: 42', state);
    expect(state.id).toBe('42');
  });

  test('parses retry field as number', () => {
    const state = { event: 'message', data: '', id: undefined as string | undefined, retry: undefined as number | undefined };
    parseSseLine('retry: 5000', state);
    expect(state.retry).toBe(5000);
  });

  test('ignores non-numeric retry field', () => {
    const state = { event: 'message', data: '', id: undefined as string | undefined, retry: undefined as number | undefined };
    parseSseLine('retry: abc', state);
    expect(state.retry).toBeUndefined();
  });

  test('ignores comment lines', () => {
    const state = { event: 'message', data: '', id: undefined as string | undefined, retry: undefined as number | undefined };
    parseSseLine(': keep-alive', state);
    expect(state).toEqual({ event: 'message', data: '', id: undefined, retry: undefined });
  });

  test('ignores unknown fields', () => {
    const state = { event: 'message', data: '', id: undefined as string | undefined, retry: undefined as number | undefined };
    parseSseLine('unknown: value', state);
    expect(state).toEqual({ event: 'message', data: '', id: undefined, retry: undefined });
  });
});

describe('SseStream', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test('parses SSE events from a stream', async () => {
    const sseText = 'event: fault\ndata: {"id":"f1"}\n\nevent: fault\ndata: {"id":"f2"}\n\n';
    const encoder = new TextEncoder();

    const mockFetch = vi.fn(async () =>
      new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(sseText));
          controller.close();
        },
      }), { status: 200 }),
    );

    const stream = new SseStream('http://localhost/api/v1/faults/stream', {
      fetch: mockFetch,
      maxRetries: 0,
    });

    const events: SseEvent[] = [];
    for await (const event of stream) {
      events.push(event);
    }

    expect(events).toHaveLength(2);
    expect(events[0]).toEqual({ event: 'fault', data: { id: 'f1' }, id: undefined });
    expect(events[1]).toEqual({ event: 'fault', data: { id: 'f2' }, id: undefined });
  });

  test('handles non-JSON data gracefully', async () => {
    const sseText = 'data: not-json\n\n';
    const encoder = new TextEncoder();

    const mockFetch = vi.fn(async () =>
      new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(sseText));
          controller.close();
        },
      }), { status: 200 }),
    );

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 0,
    });

    const events: SseEvent[] = [];
    for await (const event of stream) {
      events.push(event);
    }

    expect(events).toHaveLength(1);
    expect(events[0].data).toBe('not-json');
  });

  test('throws MedkitError on initial 4xx response', async () => {
    const mockFetch = vi.fn(async () =>
      new Response(JSON.stringify({ error_code: 'unauthorized', message: 'No token' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 0,
    });

    const events: SseEvent[] = [];
    try {
      for await (const _event of stream) {
        events.push(_event);
      }
      expect.unreachable('should have thrown');
    } catch (e) {
      expect(e).toMatchObject({ status: 401, code: 'unauthorized' });
      expect(e).toBeInstanceOf(Error);
      expect((e as Error).stack).toBeDefined();
    }
    expect(events).toHaveLength(0);
  });

  test('can be closed mid-stream', async () => {
    const encoder = new TextEncoder();

    const mockFetch = vi.fn(async () =>
      new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('data: {"n":1}\n\n'));
          // Don't close - simulates an ongoing stream
        },
      }), { status: 200 }),
    );

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 0,
    });

    const events: SseEvent[] = [];
    for await (const event of stream) {
      events.push(event);
      stream.close();
    }

    expect(events).toHaveLength(1);
  });

  test('reconnects on network error with backoff', async () => {
    let callCount = 0;
    const encoder = new TextEncoder();

    const mockFetch = vi.fn(async () => {
      callCount++;
      if (callCount === 1) {
        return new Response(new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode('data: {"n":1}\n\n'));
          },
          pull(controller) {
            controller.error(new Error('connection reset'));
          },
        }), { status: 200 });
      }
      return new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('data: {"n":2}\n\n'));
          controller.close();
        },
      }), { status: 200 });
    });

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 2,
      initialDelay: 10,
      maxDelay: 50,
    });

    const events: SseEvent[] = [];
    for await (const event of stream) {
      events.push(event);
    }

    expect(events).toHaveLength(2);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  test('throws immediately on auth failure during reconnect (no retry)', async () => {
    let callCount = 0;
    const encoder = new TextEncoder();

    const mockFetch = vi.fn(async () => {
      callCount++;
      if (callCount === 1) {
        return new Response(new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode('data: {"n":1}\n\n'));
          },
          pull(controller) {
            controller.error(new Error('connection reset'));
          },
        }), { status: 200 });
      }
      return new Response(JSON.stringify({ error_code: 'unauthorized', message: 'Token expired' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    });

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 5,
      initialDelay: 10,
    });

    const events: SseEvent[] = [];
    try {
      for await (const event of stream) {
        events.push(event);
      }
      expect.unreachable('should have thrown');
    } catch (e) {
      expect(e).toMatchObject({ status: 401, code: 'unauthorized' });
    }

    expect(events).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  test('uses server retry delay when provided', async () => {
    let callCount = 0;
    const encoder = new TextEncoder();
    const callTimestamps: number[] = [];

    const mockFetch = vi.fn(async () => {
      callTimestamps.push(Date.now());
      callCount++;
      if (callCount === 1) {
        return new Response(new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode('retry: 50\ndata: {"n":1}\n\n'));
          },
          pull(controller) {
            controller.error(new Error('disconnect'));
          },
        }), { status: 200 });
      }
      return new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('data: {"n":2}\n\n'));
          controller.close();
        },
      }), { status: 200 });
    });

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 2,
      initialDelay: 10000,
    });

    const events: SseEvent[] = [];
    for await (const event of stream) {
      events.push(event);
    }

    expect(events).toHaveLength(2);
    const reconnectDelay = callTimestamps[1]! - callTimestamps[0]!;
    expect(reconnectDelay).toBeLessThan(500);
  });

  test('sends Last-Event-ID on reconnect', async () => {
    let callCount = 0;
    const encoder = new TextEncoder();
    const capturedHeaders: (Headers | undefined)[] = [];

    const mockFetch = vi.fn(async (url: string, init?: RequestInit) => {
      capturedHeaders.push(init?.headers ? new Headers(init.headers) : undefined);
      callCount++;
      if (callCount === 1) {
        return new Response(new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode('id: 42\ndata: {"n":1}\n\n'));
          },
          pull(controller) {
            controller.error(new Error('disconnect'));
          },
        }), { status: 200 });
      }
      return new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('data: {"n":2}\n\n'));
          controller.close();
        },
      }), { status: 200 });
    });

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 2,
      initialDelay: 10,
    });

    const events: SseEvent[] = [];
    for await (const event of stream) {
      events.push(event);
    }

    expect(capturedHeaders[1]?.get('Last-Event-ID')).toBe('42');
  });

  test('handles SSE data split across multiple chunks', async () => {
    const encoder = new TextEncoder();
    const chunk1 = 'data: {"id":';
    const chunk2 = '"f1"}\n\ndata: {"id":"f2"}\n\n';

    const mockFetch = vi.fn(async () =>
      new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(chunk1));
          controller.enqueue(encoder.encode(chunk2));
          controller.close();
        },
      }), { status: 200 }),
    );

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 0,
    });

    const events: SseEvent[] = [];
    for await (const event of stream) {
      events.push(event);
    }

    expect(events).toHaveLength(2);
    expect(events[0].data).toEqual({ id: 'f1' });
    expect(events[1].data).toEqual({ id: 'f2' });
  });

  test('throws after maxRetries exhaustion', async () => {
    const mockFetch = vi.fn(async () => {
      throw new TypeError('Failed to fetch');
    });

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 2,
      initialDelay: 10,
      maxDelay: 20,
    });

    try {
      for await (const _event of stream) {
        // should not yield
      }
      expect.unreachable('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(TypeError);
      expect((e as Error).message).toBe('Failed to fetch');
    }

    // Initial attempt + 2 retries = 3 total calls
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  test('throws on response with no body', async () => {
    const mockFetch = vi.fn(async () =>
      new Response(null, { status: 200 }),
    );

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 0,
    });

    try {
      for await (const _event of stream) {
        // should not yield
      }
      expect.unreachable('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(Error);
      expect(e).toMatchObject({ code: 'unknown', status: 0 });
    }
  });

  test('throws on SSE buffer overflow', async () => {
    const encoder = new TextEncoder();
    // Create a huge chunk without newlines
    const hugeChunk = 'x'.repeat(1024 * 1024 + 1);

    const mockFetch = vi.fn(async () =>
      new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(hugeChunk));
          controller.close();
        },
      }), { status: 200 }),
    );

    const stream = new SseStream('http://localhost/test', {
      fetch: mockFetch,
      maxRetries: 0,
    });

    try {
      for await (const _event of stream) {
        // should not yield
      }
      expect.unreachable('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(Error);
      expect(e).toMatchObject({ code: 'sse-buffer-overflow' });
    }
  });
});
