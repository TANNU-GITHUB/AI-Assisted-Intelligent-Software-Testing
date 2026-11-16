export type OAuthProvider = 'google' | 'github';

const STATE_TTL_MS = 10 * 60 * 1000;
const STORAGE_KEYS: Record<OAuthProvider, string> = {
  google: 'bugai_oauth_state',
  github: 'bugai_github_oauth_state',
};

type StoredOAuthState = {
  value: string;
  expires: number;
};

function isStoredOAuthState(value: unknown): value is StoredOAuthState {
  if (typeof value !== 'object' || value === null) return false;
  const record = value as Record<string, unknown>;
  return (
    typeof record.value === 'string' &&
    typeof record.expires === 'number' &&
    Number.isFinite(record.expires)
  );
}

export function saveOAuthState(provider: OAuthProvider, state: string): void {
  const storedState: StoredOAuthState = {
    value: state,
    expires: Date.now() + STATE_TTL_MS,
  };
  window.localStorage.setItem(STORAGE_KEYS[provider], JSON.stringify(storedState));
}

export function consumeOAuthState(provider: OAuthProvider): string | null {
  const key = STORAGE_KEYS[provider];
  const raw = window.localStorage.getItem(key);
  window.localStorage.removeItem(key);
  if (!raw) return null;

  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }

  if (!isStoredOAuthState(value) || Date.now() >= value.expires) return null;
  return value.value;
}
