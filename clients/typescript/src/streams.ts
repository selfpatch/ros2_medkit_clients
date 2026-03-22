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

import type { SseOptions, EntityType, SubscriptionEntityType } from './types.js';
import { SseStream } from './sse.js';

/** High-level SSE stream helpers attached to the client. */
export interface StreamHelpers {
  /** Stream real-time fault events from GET /faults/stream. */
  faults(options?: SseOptions): SseStream;

  /**
   * Stream trigger notification events.
   * GET /{entityType}/{entityId}/triggers/{triggerId}/events
   */
  triggerEvents(
    entityType: EntityType,
    entityId: string,
    triggerId: string,
    options?: SseOptions,
  ): SseStream;

  /**
   * Stream cyclic subscription data events.
   * GET /{entityType}/{entityId}/cyclic-subscriptions/{subscriptionId}/events
   * Note: areas do not support cyclic subscriptions.
   */
  subscriptionEvents(
    entityType: SubscriptionEntityType,
    entityId: string,
    subscriptionId: string,
    options?: SseOptions,
  ): SseStream;
}

/** Create stream helpers bound to a base URL and auth headers. */
export function createStreamHelpers(
  baseUrl: string,
  headers: Record<string, string>,
  defaultSseOptions: SseOptions,
  fetchFn?: typeof globalThis.fetch,
): StreamHelpers {
  function makeSseStream(path: string, options?: SseOptions): SseStream {
    return new SseStream(`${baseUrl}${path}`, {
      headers,
      fetch: fetchFn,
      maxRetries: options?.maxRetries ?? defaultSseOptions.maxRetries,
      initialDelay: options?.initialDelay ?? defaultSseOptions.initialDelay,
      maxDelay: options?.maxDelay ?? defaultSseOptions.maxDelay,
    });
  }

  return {
    faults(options?: SseOptions): SseStream {
      return makeSseStream('/faults/stream', options);
    },

    triggerEvents(
      entityType: EntityType,
      entityId: string,
      triggerId: string,
      options?: SseOptions,
    ): SseStream {
      return makeSseStream(
        `/${entityType}/${entityId}/triggers/${triggerId}/events`,
        options,
      );
    },

    subscriptionEvents(
      entityType: SubscriptionEntityType,
      entityId: string,
      subscriptionId: string,
      options?: SseOptions,
    ): SseStream {
      return makeSseStream(
        `/${entityType}/${entityId}/cyclic-subscriptions/${subscriptionId}/events`,
        options,
      );
    },
  };
}
