const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

const SESSION_KEY = "joblens_auth_session";

export type AuthUser = {
  id: string;
  email?: string;
  user_metadata?: {
    name?: string;
    full_name?: string;
  };
};

export type AuthSession = {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  user: AuthUser;
};

type SupabaseAuthResponse = {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  user?: AuthUser;
  id?: string;
  email?: string;
  error_description?: string;
  msg?: string;
};

function assertAuthConfig() {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error("Missing Supabase frontend auth env values");
  }
}

function buildHeaders() {
  assertAuthConfig();

  return {
    "Content-Type": "application/json",
    apikey: SUPABASE_ANON_KEY,
  };
}

function normalizeSession(data: SupabaseAuthResponse): AuthSession {
  if (!data.access_token || !data.refresh_token || !data.user) {
    throw new Error(
      data.error_description || data.msg || "Authentication did not return a session"
    );
  }

  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Date.now() + (data.expires_in ?? 3600) * 1000,
    user: data.user,
  };
}

async function authFetch(path: string, body: object) {
  assertAuthConfig();

  const response = await fetch(`${SUPABASE_URL}/auth/v1${path}`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(body),
  });
  const data = (await response.json()) as SupabaseAuthResponse;

  if (!response.ok) {
    throw new Error(data.error_description || data.msg || "Authentication failed");
  }

  return data;
}

export function getStoredSession(): AuthSession | null {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function storeSession(session: AuthSession) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearStoredSession() {
  localStorage.removeItem(SESSION_KEY);
}

export async function signInWithPassword(email: string, password: string) {
  const data = await authFetch("/token?grant_type=password", {
    email,
    password,
  });
  const session = normalizeSession(data);
  storeSession(session);
  return session;
}

export async function signUpWithPassword(
  email: string,
  password: string,
  name: string
) {
  const redirectTo = encodeURIComponent(window.location.origin);
  const data = await authFetch(`/signup?redirect_to=${redirectTo}`, {
    email,
    password,
    data: {
      name,
    },
  });
  if (!data.access_token || !data.refresh_token) {
    return null;
  }

  const session = normalizeSession(data);
  storeSession(session);
  return session;
}

export async function refreshSession(session: AuthSession) {
  const data = await authFetch("/token?grant_type=refresh_token", {
    refresh_token: session.refresh_token,
  });
  const nextSession = normalizeSession(data);
  storeSession(nextSession);
  return nextSession;
}

export async function getValidSession() {
  const session = getStoredSession();
  if (!session) {
    return null;
  }

  if (Date.now() < session.expires_at - 60_000) {
    return session;
  }

  try {
    return await refreshSession(session);
  } catch {
    clearStoredSession();
    return null;
  }
}

export async function signOut(session: AuthSession | null) {
  if (session) {
    try {
      assertAuthConfig();
      await fetch(`${SUPABASE_URL}/auth/v1/logout`, {
        method: "POST",
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${session.access_token}`,
        },
      });
    } catch {
      // Local sign-out should still happen if the network request fails.
    }
  }

  clearStoredSession();
}
