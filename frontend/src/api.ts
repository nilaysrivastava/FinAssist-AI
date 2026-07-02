import type { ChatMessage, User } from "./types";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_BASE ||
  "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("finassist_token");
}

export function setToken(token: string) {
  localStorage.setItem("finassist_token", token);
}

export function clearToken() {
  localStorage.removeItem("finassist_token");
}

function getErrorMessage(data: any): string {
  if (!data) return "Something went wrong";

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        const loc = Array.isArray(item.loc) ? item.loc.join(".") : "";
        const msg = item.msg || JSON.stringify(item);
        return loc ? `${loc}: ${msg}` : msg;
      })
      .join(", ");
  }

  if (typeof data.detail === "object") {
    return (
      data.detail.message || data.detail.reason || JSON.stringify(data.detail)
    );
  }

  if (typeof data.message === "string") {
    return data.message;
  }

  return "Something went wrong";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  let res: Response;

  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new Error(
      `Unable to connect to backend at ${API_BASE}. Check Render status, VITE_API_BASE_URL, and CORS settings.`
    );
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(getErrorMessage(data));
  }

  return data as T;
}

export async function login(email: string, password: string) {
  return request<{ token: string; user: User }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function signup(name: string, email: string, password: string) {
  return request<{ token: string; user: User }>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export async function me() {
  return request<User>("/api/me");
}

export async function sendChat(message: string, history: ChatMessage[]) {
  return request<{
    answer: string;
    sources: any[];
    tool_trace: any[];
    blocked: boolean;
    needs_human_approval: boolean;
    email_offer: any | null;
  }>("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      history: history.map((m) => ({
        role: m.role,
        content: m.content,
      })),
    }),
  });
}

export async function sendEmailOffer(offerId: string) {
  return request<{
    allowed: boolean;
    message: string;
    email_id?: string;
    recipient_masked?: string;
  }>("/api/email/send-offer", {
    method: "POST",
    body: JSON.stringify({
      offer_id: offerId,
    }),
  });
}
