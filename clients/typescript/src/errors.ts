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

import type { Middleware } from 'openapi-fetch';

/** Structured error returned by the Medkit gateway. */
export interface MedkitError {
  /** HTTP status code. */
  status: number;
  /** Error code from GenericError.error_code. */
  code: string;
  /** Human-readable error message. */
  message: string;
  /** Additional error details from GenericError.parameters. */
  details?: Record<string, unknown>;
}

/** Error class thrown by SSE streams and other async operations. Extends Error for stack traces. */
export class MedkitApiError extends Error implements MedkitError {
  readonly status: number;
  readonly code: string;
  readonly details?: Record<string, unknown>;

  constructor(error: MedkitError) {
    super(error.message);
    this.name = 'MedkitApiError';
    this.status = error.status;
    this.code = error.code;
    this.details = error.details;
  }
}

/** Type guard for MedkitError. */
export function isMedkitError(value: unknown): value is MedkitError {
  return (
    typeof value === 'object' &&
    value !== null &&
    'status' in value &&
    'code' in value &&
    'message' in value &&
    typeof (value as MedkitError).status === 'number' &&
    typeof (value as MedkitError).code === 'string' &&
    typeof (value as MedkitError).message === 'string'
  );
}

/**
 * Parse a response body into a MedkitError.
 * If the body matches GenericError schema, extract fields.
 * Otherwise, return a fallback error with the status code.
 */
export function parseGenericError(body: unknown, status: number): MedkitError {
  if (
    typeof body === 'object' &&
    body !== null &&
    'error_code' in body &&
    'message' in body &&
    typeof (body as Record<string, unknown>).error_code === 'string' &&
    typeof (body as Record<string, unknown>).message === 'string'
  ) {
    const b = body as Record<string, unknown>;
    return {
      status,
      code: b.error_code as string,
      message: b.message as string,
      details: b.parameters as Record<string, unknown> | undefined,
    };
  }

  return {
    status,
    code: 'unknown',
    message: `Request failed with status ${status}`,
    details: undefined,
  };
}

/**
 * openapi-fetch middleware that intercepts non-2xx responses and
 * transforms them into MedkitError JSON responses.
 */
export const errorMiddleware: Middleware = {
  async onResponse({ response }) {
    if (response.ok) {
      return undefined; // pass through
    }

    let body: unknown;
    try {
      body = await response.clone().json();
    } catch {
      body = null;
    }

    const medkitError = parseGenericError(body, response.status);

    return new Response(JSON.stringify(medkitError), {
      status: response.status,
      headers: { 'Content-Type': 'application/json' },
    });
  },
};
