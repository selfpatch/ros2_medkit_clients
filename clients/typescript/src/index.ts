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

// Client factory
export { createMedkitClient, normalizeBaseUrl, getTimeoutForPath } from './client.js';
export type { MedkitClient } from './client.js';

// Error types and utilities
export { parseGenericError, isMedkitError, errorMiddleware, MedkitApiError } from './errors.js';
export type { MedkitError } from './errors.js';

// SSE
export { SseStream } from './sse.js';

// Stream helpers (exposed via client.streams, but also importable standalone)
export { createStreamHelpers } from './streams.js';
export type { StreamHelpers } from './streams.js';

// Types
export type {
  paths,
  components,
  GenericError,
  MedkitClientOptions,
  SseEvent,
  SseOptions,
  TimeoutConfig,
  EntityType,
  SubscriptionEntityType,
} from './types.js';
