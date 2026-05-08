import { clearStoredAuthSession, ensureFreshSession, getStoredAuthSession } from '../auth/session';

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

function buildHeaders(init?: RequestInit, token?: string): Headers {
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has('Content-Type') && init?.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  const resolvedToken = token ?? getStoredAuthSession()?.accessToken;
  if (resolvedToken) {
    headers.set('Authorization', `Bearer ${resolvedToken}`);
  }
  return headers;
}

export async function apiRequest<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const activeSession = await ensureFreshSession();
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...init,
    headers: buildHeaders(init, token ?? activeSession?.accessToken),
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredAuthSession();
    }
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string; code?: string };
      detail = body.detail ?? body.code ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function extractFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) {
    return null;
  }
  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(contentDisposition);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }
  const plainMatch = /filename="?([^";]+)"?/i.exec(contentDisposition);
  return plainMatch?.[1] ?? null;
}

export async function apiDownload(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const activeSession = await ensureFreshSession();
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: buildHeaders(undefined, activeSession?.accessToken),
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredAuthSession();
    }
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string; code?: string };
      detail = body.detail ?? body.code ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  return {
    blob: await response.blob(),
    filename: extractFilename(response.headers.get('Content-Disposition')),
  };
}
