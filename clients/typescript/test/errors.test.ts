import { describe, test, expect } from 'vitest';
import { isMedkitError, parseGenericError, errorMiddleware } from '../src/errors.js';
import type { MedkitError } from '../src/errors.js';

describe('parseGenericError', () => {
  test('parses valid GenericError JSON', () => {
    const body = {
      error_code: 'entity-not-found',
      message: 'Entity my_node not found',
    };
    const result = parseGenericError(body, 404);
    expect(result).toEqual({
      status: 404,
      code: 'entity-not-found',
      error_code: 'entity-not-found',
      message: 'Entity my_node not found',
      details: undefined,
      parameters: undefined,
    });
  });

  test('parses GenericError with parameters', () => {
    const body = {
      error_code: 'validation-error',
      message: 'Invalid input',
      parameters: { field: 'name', reason: 'too long' },
    };
    const result = parseGenericError(body, 400);
    expect(result).toEqual({
      status: 400,
      code: 'validation-error',
      error_code: 'validation-error',
      message: 'Invalid input',
      details: { field: 'name', reason: 'too long' },
      parameters: { field: 'name', reason: 'too long' },
    });
  });

  test('returns fallback for non-GenericError body', () => {
    const result = parseGenericError('plain text', 500);
    expect(result).toEqual({
      status: 500,
      code: 'unknown',
      error_code: 'unknown',
      message: 'Request failed with status 500',
      details: undefined,
      parameters: undefined,
    });
  });

  test('returns fallback for null body', () => {
    const result = parseGenericError(null, 502);
    expect(result.status).toBe(502);
    expect(result.code).toBe('unknown');
    expect(result.error_code).toBe('unknown');
  });
});

describe('isMedkitError', () => {
  test('returns true for MedkitError objects', () => {
    const err: MedkitError = { status: 404, code: 'not-found', error_code: 'not-found', message: 'gone' };
    expect(isMedkitError(err)).toBe(true);
  });

  test('returns false for non-error objects', () => {
    expect(isMedkitError({ name: 'test' })).toBe(false);
    expect(isMedkitError(null)).toBe(false);
    expect(isMedkitError('string')).toBe(false);
  });
});

describe('errorMiddleware', () => {
  test('passes through 2xx responses unchanged', async () => {
    const response = new Response(JSON.stringify({ items: [] }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

    const result = await errorMiddleware.onResponse!({
      request: new Request('http://localhost/api/v1/apps'),
      response,
      options: {} as never,
    });

    // undefined means no modification
    expect(result).toBeUndefined();
  });

  test('transforms 4xx GenericError into MedkitError response', async () => {
    const body = JSON.stringify({
      error_code: 'entity-not-found',
      message: 'Entity x not found',
    });
    const response = new Response(body, {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    });

    const result = await errorMiddleware.onResponse!({
      request: new Request('http://localhost/api/v1/apps/x'),
      response,
      options: {} as never,
    });

    expect(result).toBeInstanceOf(Response);
    const parsed = await result!.json();
    expect(parsed.status).toBe(404);
    expect(parsed.code).toBe('entity-not-found');
    expect(parsed.error_code).toBe('entity-not-found');
    expect(parsed.message).toBe('Entity x not found');
  });

  test('transforms 5xx without GenericError into fallback MedkitError', async () => {
    const response = new Response('Internal Server Error', {
      status: 500,
      headers: { 'Content-Type': 'text/plain' },
    });

    const result = await errorMiddleware.onResponse!({
      request: new Request('http://localhost/api/v1/health'),
      response,
      options: {} as never,
    });

    expect(result).toBeInstanceOf(Response);
    const parsed = await result!.json();
    expect(parsed.status).toBe(500);
    expect(parsed.code).toBe('unknown');
  });
});
