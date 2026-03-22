import { describe, test, expect, vi, afterEach } from 'vitest';
import { createStreamHelpers } from '../src/streams.js';
import type { SseEvent } from '../src/types.js';

function mockSseResponse(events: string): typeof globalThis.fetch {
  const encoder = new TextEncoder();
  return vi.fn(async () =>
    new Response(new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(events));
        controller.close();
      },
    }), { status: 200 }),
  );
}

describe('createStreamHelpers', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test('faults() streams from /faults/stream', async () => {
    const mockFetch = mockSseResponse('data: {"id":"f1"}\n\n');
    const streams = createStreamHelpers(
      'http://localhost:8080/api/v1',
      {},
      {},
      mockFetch,
    );

    const events: SseEvent[] = [];
    for await (const event of streams.faults()) {
      events.push(event);
    }

    expect(events).toHaveLength(1);
    expect(events[0].data).toEqual({ id: 'f1' });
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/faults/stream',
      expect.anything(),
    );
  });

  test('triggerEvents() builds correct URL for apps', async () => {
    const mockFetch = mockSseResponse('data: {"trigger":"t1"}\n\n');
    const streams = createStreamHelpers(
      'http://localhost:8080/api/v1',
      {},
      {},
      mockFetch,
    );

    const events: SseEvent[] = [];
    for await (const event of streams.triggerEvents('apps', 'my_node', 'trig_1')) {
      events.push(event);
    }

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/apps/my_node/triggers/trig_1/events',
      expect.anything(),
    );
    expect(events).toHaveLength(1);
  });

  test('triggerEvents() works for all entity types', async () => {
    for (const entityType of ['apps', 'areas', 'components', 'functions'] as const) {
      const mockFetch = mockSseResponse('data: {}\n\n');
      const streams = createStreamHelpers('http://localhost/api/v1', {}, {}, mockFetch);

      for await (const _event of streams.triggerEvents(entityType, 'e1', 't1')) {
        // consume
      }

      expect(mockFetch).toHaveBeenCalledWith(
        `http://localhost/api/v1/${entityType}/e1/triggers/t1/events`,
        expect.anything(),
      );
    }
  });

  test('subscriptionEvents() builds correct URL', async () => {
    const mockFetch = mockSseResponse('data: {"value":42}\n\n');
    const streams = createStreamHelpers('http://localhost/api/v1', {}, {}, mockFetch);

    const events: SseEvent[] = [];
    for await (const event of streams.subscriptionEvents('components', 'lidar', 'sub_1')) {
      events.push(event);
    }

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost/api/v1/components/lidar/cyclic-subscriptions/sub_1/events',
      expect.anything(),
    );
  });

  test('passes auth headers to SSE stream', async () => {
    const capturedHeaders: Record<string, string>[] = [];
    const encoder = new TextEncoder();
    const mockFetch = vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.headers) {
        const h: Record<string, string> = {};
        new Headers(init.headers as HeadersInit).forEach((v, k) => { h[k] = v; });
        capturedHeaders.push(h);
      }
      return new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('data: {}\n\n'));
          controller.close();
        },
      }), { status: 200 });
    });

    const streams = createStreamHelpers(
      'http://localhost/api/v1',
      { Authorization: 'Bearer tok123' },
      {},
      mockFetch,
    );

    for await (const _e of streams.faults()) { /* consume */ }

    expect(capturedHeaders[0]?.['authorization']).toBe('Bearer tok123');
  });
});
