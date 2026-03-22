// Copyright 2026 bburda
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import type { SseEvent, SseOptions } from './types.js';
import { parseGenericError, isMedkitError, MedkitApiError } from './errors.js';

/** Internal state for parsing SSE lines. */
export interface SseLineState {
  event: string;
  data: string;
  id: string | undefined;
  retry: number | undefined;
}

/** Parse a single SSE line into the accumulator state. */
export function parseSseLine(line: string, state: SseLineState): void {
  if (line.startsWith(':')) {
    return; // comment
  }

  const colonIndex = line.indexOf(':');
  if (colonIndex === -1) {
    return; // no field
  }

  const field = line.slice(0, colonIndex);
  const value = line[colonIndex + 1] === ' ' ? line.slice(colonIndex + 2) : line.slice(colonIndex + 1);

  switch (field) {
    case 'event':
      state.event = value;
      break;
    case 'data':
      state.data = state.data ? `${state.data}\n${value}` : value;
      break;
    case 'id':
      state.id = value;
      break;
    case 'retry': {
      const ms = parseInt(value, 10);
      if (!isNaN(ms)) {
        state.retry = ms;
      }
      break;
    }
    default:
      break;
  }
}

interface SseStreamOptions extends SseOptions {
  headers?: Record<string, string>;
  fetch?: typeof globalThis.fetch;
}

/**
 * SSE stream using fetch + ReadableStream.
 * Implements async iterator protocol for `for await...of` consumption.
 * Supports reconnection with exponential backoff and Last-Event-ID.
 */
export class SseStream implements AsyncIterable<SseEvent> {
  private url: string;
  private headers: Record<string, string>;
  private fetchFn: typeof globalThis.fetch;
  private maxRetries: number;
  private initialDelay: number;
  private maxDelay: number;
  private lastEventId: string | undefined;
  private serverRetryDelay: number | undefined;
  private closed = false;
  private static readonly MAX_BUFFER_SIZE = 1024 * 1024; // 1 MB
  private static readonly MAX_DATA_SIZE = 256 * 1024; // 256 KB
  private abortController: AbortController | null = null;
  private _eventsYielded = false;
  private sleepTimer: ReturnType<typeof setTimeout> | null = null;
  private sleepResolve: (() => void) | null = null;

  constructor(url: string, options: SseStreamOptions = {}) {
    this.url = url;
    this.headers = options.headers ?? {};
    this.fetchFn = options.fetch ?? globalThis.fetch;
    this.maxRetries = options.maxRetries ?? 5;
    this.initialDelay = options.initialDelay ?? 1000;
    this.maxDelay = options.maxDelay ?? 30000;
  }

  close(): void {
    this.closed = true;
    this.abortController?.abort();
    if (this.sleepTimer) {
      clearTimeout(this.sleepTimer);
      this.sleepTimer = null;
    }
    if (this.sleepResolve) {
      this.sleepResolve();
      this.sleepResolve = null;
    }
  }

  async *[Symbol.asyncIterator](): AsyncGenerator<SseEvent> {
    let retries = 0;

    while (!this.closed) {
      try {
        yield* this.connectAndStream();
        return; // clean close
      } catch (error) {
        if (this.closed) return;

        if (isMedkitError(error)) {
          throw error; // HTTP errors (4xx/5xx) are not retried
        }

        // Reset retry counter if we received events before this disconnect
        if (this._eventsYielded) {
          retries = 0;
          this._eventsYielded = false;
        }

        retries++;
        if (retries > this.maxRetries) {
          throw error;
        }

        // Clamp server retry delay: minimum 100ms to prevent reconnect storms,
        // maximum maxDelay. SSE spec allows retry:0 for immediate reconnect,
        // but we enforce a floor to protect against malicious servers.
        const baseDelay = this.serverRetryDelay !== undefined
          ? Math.max(100, Math.min(this.serverRetryDelay, this.maxDelay))
          : Math.min(this.initialDelay * Math.pow(2, retries - 1), this.maxDelay);
        await new Promise<void>((resolve) => {
          this.sleepResolve = resolve;
          this.sleepTimer = setTimeout(() => {
            this.sleepTimer = null;
            this.sleepResolve = null;
            resolve();
          }, baseDelay);
        });
      }
    }
  }

  private async *connectAndStream(): AsyncGenerator<SseEvent> {
    this.abortController = new AbortController();

    const reqHeaders: Record<string, string> = {
      Accept: 'text/event-stream',
      ...this.headers,
    };
    if (this.lastEventId) {
      reqHeaders['Last-Event-ID'] = this.lastEventId;
    }

    const response = await this.fetchFn(this.url, {
      headers: reqHeaders,
      signal: this.abortController.signal,
    });

    if (!response.ok) {
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        body = null;
      }
      throw new MedkitApiError(parseGenericError(body, response.status));
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new MedkitApiError(parseGenericError(null, 0));
    }

    const decoder = new TextDecoder();
    let buffer = '';
    const state: SseLineState = { event: 'message', data: '', id: undefined, retry: undefined };

    try {
      while (!this.closed) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        if (buffer.length > SseStream.MAX_BUFFER_SIZE) {
          throw new MedkitApiError({
            status: 0,
            code: 'sse-buffer-overflow',
            error_code: 'sse-buffer-overflow',
            message: 'SSE buffer exceeded maximum size (1 MB). The server may be sending malformed data.',
          });
        }

        const rawLines = buffer.split('\n');
        buffer = rawLines.pop() ?? '';
        const lines = rawLines.map((l) => l.replace(/\r$/, ''));

        for (const line of lines) {
          if (line === '') {
            if (state.data) {
              let parsedData: unknown;
              try {
                parsedData = JSON.parse(state.data);
              } catch {
                parsedData = state.data;
              }

              const event: SseEvent = {
                event: state.event,
                data: parsedData,
                id: state.id,
              };

              if (state.id) {
                this.lastEventId = state.id;
              }
              if (state.retry !== undefined) {
                this.serverRetryDelay = state.retry;
              }

              this._eventsYielded = true;
              yield event;
            }

            state.event = 'message';
            state.data = '';
            state.id = undefined;
            state.retry = undefined;
          } else {
            parseSseLine(line, state);
            if (state.data.length > SseStream.MAX_DATA_SIZE) {
              throw new MedkitApiError({
                status: 0,
                code: 'sse-data-overflow',
                error_code: 'sse-data-overflow',
                message: 'SSE event data exceeded maximum size (256 KB).',
              });
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}
