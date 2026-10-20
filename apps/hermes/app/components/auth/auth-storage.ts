const STORAGE_EMAIL_KEY = 'hermes_auth_email';
const STORAGE_ONBOARDING_TOKEN_KEY = 'hermes_onboarding_token';
const STORAGE_KNOWN_USERS_KEY = 'hermes_known_emails';

export function getStoredEmail(): string {
  if (typeof window === 'undefined') return '';
  return window.sessionStorage.getItem(STORAGE_EMAIL_KEY) || '';
}

export function setStoredEmail(email: string): void {
  if (typeof window === 'undefined') return;
  const trimmed = email.trim();
  if (trimmed) {
    window.sessionStorage.setItem(STORAGE_EMAIL_KEY, trimmed);
  }
}

export function clearStoredEmail(): void {
  if (typeof window === 'undefined') return;
  window.sessionStorage.removeItem(STORAGE_EMAIL_KEY);
}

export function getStoredOnboardingToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.sessionStorage.getItem(STORAGE_ONBOARDING_TOKEN_KEY);
}

export function setStoredOnboardingToken(token: string | null): void {
  if (typeof window === 'undefined') return;
  if (token) {
    window.sessionStorage.setItem(STORAGE_ONBOARDING_TOKEN_KEY, token);
  } else {
    window.sessionStorage.removeItem(STORAGE_ONBOARDING_TOKEN_KEY);
  }
}

export function clearStoredOnboardingToken(): void {
  if (typeof window === 'undefined') return;
  window.sessionStorage.removeItem(STORAGE_ONBOARDING_TOKEN_KEY);
}

export function isKnownUserEmail(email: string): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const raw = window.localStorage.getItem(STORAGE_KNOWN_USERS_KEY);
    if (!raw) return false;
    const list = JSON.parse(raw) as string[];
    return Array.isArray(list) && list.includes(email.trim().toLowerCase());
  } catch {
    return false;
  }
}

export function markUserEmailAsKnown(email: string): void {
  if (typeof window === 'undefined') return;
  try {
    const normalized = email.trim().toLowerCase();
    const raw = window.localStorage.getItem(STORAGE_KNOWN_USERS_KEY);
    const list: string[] = raw ? (JSON.parse(raw) as string[]) : [];
    if (!list.includes(normalized)) {
      list.push(normalized);
      window.localStorage.setItem(STORAGE_KNOWN_USERS_KEY, JSON.stringify(list));
    }
  } catch {
    // Ignore storage quota errors
  }
}
