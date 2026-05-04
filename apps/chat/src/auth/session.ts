export interface AuthClaims {
  sub: string;
  email: string;
  department: string;
  roles: string[];
  clearance: number;
  preferredUsername?: string;
  name?: string;
  raw: Record<string, unknown>;
}

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  idToken: string;
  expiresAt: number;
  refreshExpiresAt: number;
  claims: AuthClaims;
}

interface OidcTokenResponse {
  access_token: string;
  refresh_token: string;
  id_token?: string;
  expires_in: number;
  refresh_expires_in?: number;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

const SESSION_STORAGE_KEY = 'aial.auth.session';
const OIDC_STATE_KEY = 'aial.oidc.state';
const OIDC_VERIFIER_KEY = 'aial.oidc.verifier';

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=');
  return atob(padded);
}

export function decodeJwtPayload(token: string): Record<string, unknown> {
  const parts = token.split('.');
  if (parts.length < 2) {
    throw new Error('Invalid JWT');
  }
  return JSON.parse(decodeBase64Url(parts[1])) as Record<string, unknown>;
}

function parseRoles(payload: Record<string, unknown>): string[] {
  const directRoles = payload.roles;
  if (Array.isArray(directRoles)) {
    return directRoles.map((role) => String(role));
  }
  const realmAccess = payload.realm_access as { roles?: unknown } | undefined;
  if (Array.isArray(realmAccess?.roles)) {
    return realmAccess.roles.map((role) => String(role));
  }
  return [];
}

function parseClaims(payload: Record<string, unknown>): AuthClaims {
  const clearanceValue = payload.clearance;
  const clearance = typeof clearanceValue === 'number'
    ? clearanceValue
    : Number.parseInt(String(clearanceValue ?? '1'), 10) || 1;

  return {
    sub: String(payload.sub ?? ''),
    email: String(payload.email ?? ''),
    department: String(payload.department ?? 'general'),
    roles: parseRoles(payload),
    clearance,
    preferredUsername: payload.preferred_username ? String(payload.preferred_username) : undefined,
    name: payload.name ? String(payload.name) : undefined,
    raw: payload,
  };
}

function createSession(tokens: OidcTokenResponse): AuthSession {
  const claims = parseClaims(decodeJwtPayload(tokens.access_token));
  const now = Date.now();
  return {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    idToken: tokens.id_token ?? '',
    expiresAt: now + tokens.expires_in * 1000,
    refreshExpiresAt: now + (tokens.refresh_expires_in ?? tokens.expires_in) * 1000,
    claims,
  };
}

function randomString(length = 64): string {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function toBase64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

async function createCodeChallenge(verifier: string): Promise<string> {
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  return toBase64Url(hash);
}

function getKeycloakBase(): string {
  return import.meta.env.VITE_KEYCLOAK_URL ?? 'http://localhost:8080';
}

function getRealm(): string {
  return import.meta.env.VITE_KEYCLOAK_REALM ?? 'aial';
}

function getClientId(): string {
  return import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? 'aial-frontend';
}

function getRedirectUri(): string {
  return `${window.location.origin}/auth/callback`;
}

function getTokenEndpoint(): string {
  return `${getKeycloakBase()}/realms/${getRealm()}/protocol/openid-connect/token`;
}

function getLogoutEndpoint(): string {
  return `${getKeycloakBase()}/realms/${getRealm()}/protocol/openid-connect/logout`;
}

export function getStoredAuthSession(): AuthSession | null {
  const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
}

export function storeAuthSession(session: AuthSession): void {
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredAuthSession(): void {
  window.localStorage.removeItem(SESSION_STORAGE_KEY);
}

export function isSessionExpired(session: AuthSession, skewMs = 30_000): boolean {
  return session.expiresAt <= Date.now() + skewMs;
}

export function isRefreshExpired(session: AuthSession, skewMs = 30_000): boolean {
  return session.refreshExpiresAt <= Date.now() + skewMs;
}

export async function beginLoginRedirect(): Promise<void> {
  const state = randomString(24);
  const verifier = randomString(48);
  const challenge = await createCodeChallenge(verifier);
  window.sessionStorage.setItem(OIDC_STATE_KEY, state);
  window.sessionStorage.setItem(OIDC_VERIFIER_KEY, verifier);

  const params = new URLSearchParams({
    client_id: getClientId(),
    redirect_uri: getRedirectUri(),
    response_type: 'code',
    scope: 'openid profile email',
    prompt: 'login',
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  });
  window.location.href = `${getKeycloakBase()}/realms/${getRealm()}/protocol/openid-connect/auth?${params.toString()}`;
}

async function exchangeToken(params: URLSearchParams): Promise<AuthSession> {
  const response = await fetch(getTokenEndpoint(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params.toString(),
  });
  if (!response.ok) {
    throw new Error('Token exchange failed');
  }
  const body = (await response.json()) as OidcTokenResponse;
  const session = createSession(body);
  storeAuthSession(session);
  return session;
}

export async function completeLoginCallback(search: string): Promise<AuthSession> {
  const params = new URLSearchParams(search);
  const code = params.get('code');
  const returnedState = params.get('state');
  const expectedState = window.sessionStorage.getItem(OIDC_STATE_KEY);
  const verifier = window.sessionStorage.getItem(OIDC_VERIFIER_KEY);

  if (!code || !returnedState || returnedState !== expectedState || !verifier) {
    throw new Error('Invalid OIDC callback');
  }

  window.sessionStorage.removeItem(OIDC_STATE_KEY);
  window.sessionStorage.removeItem(OIDC_VERIFIER_KEY);

  return exchangeToken(
    new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: getClientId(),
      code,
      redirect_uri: getRedirectUri(),
      code_verifier: verifier,
    }),
  );
}

export async function refreshAuthSession(session: AuthSession): Promise<AuthSession> {
  const payload = decodeJwtPayload(session.accessToken);
  if (payload.iss === 'aial-local') {
    const response = await fetch(`${API_BASE}/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: session.refreshToken }),
    });
    if (!response.ok) {
      throw new Error('Local session refresh failed');
    }
    const body = (await response.json()) as OidcTokenResponse;
    const nextSession = createSession(body);
    storeAuthSession(nextSession);
    return nextSession;
  }
  return exchangeToken(
    new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: getClientId(),
      refresh_token: session.refreshToken,
    }),
  );
}

export async function loginWithPassword(username: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE}/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error('Invalid username or password');
  }
  const body = (await response.json()) as OidcTokenResponse;
  const session = createSession(body);
  storeAuthSession(session);
  return session;
}

export async function ensureFreshSession(): Promise<AuthSession | null> {
  const session = getStoredAuthSession();
  if (!session) {
    return null;
  }
  if (!isSessionExpired(session)) {
    return session;
  }
  if (isRefreshExpired(session)) {
    clearStoredAuthSession();
    return null;
  }
  try {
    return await refreshAuthSession(session);
  } catch {
    clearStoredAuthSession();
    return null;
  }
}

export function buildLogoutUrl(session: AuthSession | null): string {
  const params = new URLSearchParams({
    client_id: getClientId(),
    post_logout_redirect_uri: `${window.location.origin}/login`,
  });
  if (session?.idToken) {
    params.set('id_token_hint', session.idToken);
  }
  return `${getLogoutEndpoint()}?${params.toString()}`;
}
