// Client factory
export { createMedkitClient, normalizeBaseUrl, getTimeoutForPath } from './client.js';
export type { MedkitClient } from './client.js';

// Error types and utilities
export { parseGenericError, isMedkitError, errorMiddleware } from './errors.js';
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
  MedkitClientOptions,
  SseEvent,
  SseOptions,
  TimeoutConfig,
  EntityType,
  SubscriptionEntityType,
} from './types.js';
