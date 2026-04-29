/**
 * Tests for errorMessages utility
 */
import { describe, it, expect } from 'vitest';
import { getErrorMessage, getErrorLabel } from '../utils/errorMessages';

describe('getErrorMessage', () => {
  it('returns Vietnamese message for known error codes', () => {
    expect(getErrorMessage('timeout')).toContain('thời gian');
    expect(getErrorMessage('permission-denied')).toContain('quyền');
    expect(getErrorMessage('llm-unavailable')).toContain('AI');
  });

  it('handles RFC 9457 URL format', () => {
    const msg = getErrorMessage('https://aial.internal/errors/permission-denied');
    expect(msg).toContain('quyền');
  });

  it('returns default message for unknown error codes', () => {
    const msg = getErrorMessage('some-unknown-error');
    expect(msg).toBeTruthy();
    expect(typeof msg).toBe('string');
  });

  it('returns default message for empty string', () => {
    const msg = getErrorMessage('');
    expect(msg).toBeTruthy();
  });

  it('handles network-error code', () => {
    expect(getErrorMessage('network-error')).toContain('mạng');
  });

  it('handles auth-failed code', () => {
    expect(getErrorMessage('auth-failed')).toContain('đăng nhập');
  });
});

describe('getErrorLabel', () => {
  it('returns short Vietnamese labels', () => {
    expect(getErrorLabel('timeout')).toBeTruthy();
    expect(getErrorLabel('permission-denied')).toBeTruthy();
  });

  it('returns "Lỗi" for unknown codes', () => {
    expect(getErrorLabel('unknown-code')).toBe('Lỗi');
  });
});
