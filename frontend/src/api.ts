export type Role = "ADMINISTRATOR" | "USER";

export type CurrentUser = {
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: Role;
  mfa_enabled: boolean;
};

export type PortalApplication = {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon: string;
  category: string;
  application_type: "INTERNAL_WEB" | "INTERNAL_SERVICE" | "EXTERNAL_URL" | "API_APP";
  launch_url: string;
  enabled: boolean;
  administrator_only: boolean;
  status: "ONLINE" | "OFFLINE" | "UNKNOWN" | "MAINTENANCE";
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "https://api.blueashdigital.tech";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed." }));
    throw new Error(payload.detail ?? "Request failed.");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  login: (identifier: string, password: string) =>
    request<CurrentUser>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  me: () => request<CurrentUser>("/api/profile/me"),
  apps: () => request<PortalApplication[]>("/api/apps"),
};
