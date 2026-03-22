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

import type { paths, components } from '../generated/schema.js';

// Re-export generated types for consumer convenience
export type { paths, components };

// Schema type shortcuts
export type GenericError = components['schemas']['GenericError'];

/** Entity type strings accepted by SSE stream helpers. */
export type EntityType = 'apps' | 'areas' | 'components' | 'functions';

/** Entity types that support cyclic subscriptions (areas excluded). */
export type SubscriptionEntityType = 'apps' | 'components' | 'functions';

/** Parsed SSE event. */
export interface SseEvent {
  /** Event type (from `event:` field, defaults to 'message'). */
  event: string;
  /** Parsed JSON data (from `data:` field). */
  data: unknown;
  /** Event ID (from `id:` field). */
  id?: string;
}

/** Options for SSE stream connections. */
export interface SseOptions {
  /** Maximum number of reconnect attempts. Default: 5. */
  maxRetries?: number;
  /** Initial reconnect delay in ms. Default: 1000. */
  initialDelay?: number;
  /** Maximum reconnect delay in ms. Default: 30000. */
  maxDelay?: number;
}

/** Timeout configuration tiers. */
export interface TimeoutConfig {
  /** Default timeout in ms. Default: 10000. */
  default?: number;
  /** Timeout for operation execute/cancel in ms. Default: 30000. */
  operations?: number;
  /** Timeout for bulk data downloads in ms. Default: 300000. */
  downloads?: number;
}

/** Options for creating a Medkit client. */
export interface MedkitClientOptions {
  /** Gateway base URL. Normalized: adds http:// if missing, appends /api/v1 if missing. */
  baseUrl: string;
  /** JWT authentication. */
  auth?: {
    token: string;
  };
  /** Timeout configuration. */
  timeout?: TimeoutConfig;
  /** SSE stream defaults. */
  sse?: SseOptions;
  /** Custom fetch implementation (for testing). */
  fetch?: typeof globalThis.fetch;
}
