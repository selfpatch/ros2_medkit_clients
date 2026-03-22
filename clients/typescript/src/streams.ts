// Copyright 2026 Selfpatch contributors
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

import type { SseOptions } from './types.js';

export interface StreamHelpers {
  faults: () => void;
  triggerEvents: () => void;
  subscriptionEvents: () => void;
}

export function createStreamHelpers(
  _baseUrl: string,
  _headers: Record<string, string>,
  _sseOptions: SseOptions,
  _fetchFn?: typeof globalThis.fetch,
): StreamHelpers {
  return {
    faults: () => {},
    triggerEvents: () => {},
    subscriptionEvents: () => {},
  };
}
