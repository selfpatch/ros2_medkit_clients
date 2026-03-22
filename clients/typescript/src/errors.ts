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
