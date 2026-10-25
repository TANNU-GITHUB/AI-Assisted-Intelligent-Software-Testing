import { AUTH_COOKIE_NAME, AUTH_TOKEN_KEY } from './auth-constants';

export { AUTH_COOKIE_NAME, AUTH_TOKEN_KEY };

export type GitHubProfile = {
  connected: boolean;
  login?: string;
  avatar_url?: string | null;
  connected_at?: string;
};

export type PublicUser = {
  id: string;
  username: string;
  email: string | null;
  auth_provider: 'local' | 'google';
  created_at: string;
  github?: GitHubProfile;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: PublicUser;
};

const TOKEN_MAX_AGE_SEC = 60 * 60 * 24 * 7;

function apiUrl(path: string): string {
  const base = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');
  return `${base}${path}`;
}

async function readError(res: Response): Promise<string> {
  const data = await res.json().catch(() => null);
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  return res.statusText || 'Request failed';
}

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAccessToken(token: string) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  document.cookie = `${AUTH_COOKIE_NAME}=${encodeURIComponent(token)}; path=/; max-age=${TOKEN_MAX_AGE_SEC}; SameSite=Lax`;
}

export function clearAccessToken() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  document.cookie = `${AUTH_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax`;
}

export function authHeaders(): HeadersInit {
  const token = getAccessToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export async function registerUser(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch(apiUrl('/api/auth/register'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as AuthResponse;
  setAccessToken(data.access_token);
  return data;
}

export async function loginUser(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch(apiUrl('/api/auth/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as AuthResponse;
  setAccessToken(data.access_token);
  return data;
}

export async function fetchCurrentUser(): Promise<PublicUser | null> {
  const token = getAccessToken();
  if (!token) return null;
  const res = await fetch(apiUrl('/api/auth/me'), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 401) {
    clearAccessToken();
    return null;
  }
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as PublicUser;
}

export async function getGoogleAuthUrl(): Promise<{ url: string; state: string }> {
  const res = await fetch(apiUrl('/api/auth/google/url'));
  if (!res.ok) throw new Error(await readError(res));
  return res.json() as Promise<{ url: string; state: string }>;
}

export async function completeGoogleOAuth(code: string, state: string): Promise<AuthResponse> {
  const res = await fetch(apiUrl('/api/auth/google/callback'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, state }),
  });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as AuthResponse;
  setAccessToken(data.access_token);
  return data;
}

export function logout() {
  clearAccessToken();
}

export async function getGitHubAuthUrl(): Promise<{ url: string; state: string }> {
  const res = await fetch(apiUrl('/api/github/url'), { headers: authHeaders() });
  if (!res.ok) throw new Error(await readError(res));
  return res.json() as Promise<{ url: string; state: string }>;
}

export async function completeGitHubOAuth(code: string, state: string): Promise<GitHubProfile> {
  const res = await fetch(apiUrl('/api/github/callback'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ code, state }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json() as Promise<GitHubProfile>;
}

export async function fetchGitHubStatus(): Promise<GitHubProfile> {
  const res = await fetch(apiUrl('/api/github/status'), { headers: authHeaders() });
  if (!res.ok) throw new Error(await readError(res));
  return res.json() as Promise<GitHubProfile>;
}

export async function disconnectGitHub(): Promise<void> {
  const res = await fetch(apiUrl('/api/github/connection'), {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(await readError(res));
}
