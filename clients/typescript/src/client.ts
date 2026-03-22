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

import createClient from 'openapi-fetch';
import type { Middleware } from 'openapi-fetch';
import type { paths } from '../generated/schema.js';
import type { MedkitClientOptions, TimeoutConfig, SseOptions } from './types.js';
import { errorMiddleware } from './errors.js';
import { createStreamHelpers, type StreamHelpers } from './streams.js';

/** Default timeout values in ms. */
const DEFAULT_TIMEOUTS: Required<TimeoutConfig> = {
  default: 10_000,
  operations: 30_000,
  downloads: 300_000,
};

/** Path patterns for timeout tier matching. */
const OPERATION_PATHS = /\/executions/;
const DOWNLOAD_PATHS = /\/bulk-data\/[^/]+\/[^/]+\/download/;

/** Normalize a gateway URL: add http:// if missing, append /api/v1 if missing. */
export function normalizeBaseUrl(url: string): string {
  let normalized = url;

  // Add protocol if missing
  if (!normalized.match(/^https?:\/\//)) {
    normalized = `http://${normalized}`;
  }

  // Remove trailing slash
  normalized = normalized.replace(/\/+$/, '');

  // Add /api/v1 if not present
  if (!normalized.endsWith('/api/v1')) {
    normalized = `${normalized}/api/v1`;
  }

  return normalized;
}

/** Determine timeout for a request based on its path. */
export function getTimeoutForPath(path: string, config: TimeoutConfig): number {
  if (DOWNLOAD_PATHS.test(path)) {
    return config.downloads ?? DEFAULT_TIMEOUTS.downloads;
  }
  if (OPERATION_PATHS.test(path)) {
    return config.operations ?? DEFAULT_TIMEOUTS.operations;
  }
  return config.default ?? DEFAULT_TIMEOUTS.default;
}

/** Create timeout middleware that aborts requests after the tier-appropriate duration. */
export function createTimeoutMiddleware(config: TimeoutConfig): Middleware {
  return {
    async onRequest({ request }) {
      const timeout = getTimeoutForPath(new URL(request.url).pathname, config);
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeout);

      // Chain abort signals if one already exists
      if (request.signal) {
        request.signal.addEventListener('abort', () => {
          clearTimeout(timer);
          controller.abort();
        });
      }

      const newRequest = new Request(request, { signal: controller.signal });

      // Store cleanup in a way the response handler can access
      (newRequest as unknown as Record<string, unknown>).__timeoutTimer = timer;
      return newRequest;
    },
    async onResponse({ request }) {
      const timer = (request as unknown as Record<string, unknown>).__timeoutTimer as ReturnType<typeof setTimeout> | undefined;
      if (timer) clearTimeout(timer);
      return undefined;
    },
  };
}

/** The Medkit client type - openapi-fetch client extended with stream helpers. */
export type MedkitClient = ReturnType<typeof createClient<paths>> & {
  streams: StreamHelpers;
};

/** Create a configured Medkit gateway client. */
export function createMedkitClient(options: MedkitClientOptions): MedkitClient {
  const baseUrl = normalizeBaseUrl(options.baseUrl);

  const headers: Record<string, string> = {};
  if (options.auth?.token) {
    headers['Authorization'] = `Bearer ${options.auth.token}`;
  }

  const client = createClient<paths>({
    baseUrl,
    headers,
    ...(options.fetch ? { fetch: options.fetch } : {}),
  });

  // Register middleware: timeout first (sets abort signal), then error handling
  client.use(createTimeoutMiddleware(options.timeout ?? {}));
  client.use(errorMiddleware);

  // Attach stream helpers
  const sseOptions: SseOptions = options.sse ?? {};
  const streams = createStreamHelpers(baseUrl, headers, sseOptions, options.fetch);

  return Object.assign(client, { streams }) as MedkitClient;
}
