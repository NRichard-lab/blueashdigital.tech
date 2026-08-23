export type Role = "ADMINISTRATOR" | "USER";

export type CurrentUser = {
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: Role;
  mfa_enabled: boolean;
  permissions: string[];
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

export type ManagedUser = {
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: Role;
  enabled: boolean;
  force_password_change: boolean;
  mfa_required: boolean;
  mfa_enabled: boolean;
  created_at: string | null;
  last_login_at: string | null;
  applications_assigned: number;
  application_ids: string[];
};

export type UserListResponse = {
  items: ManagedUser[];
  total: number;
  limit: number;
  offset: number;
};

export type UserPayload = {
  username?: string;
  email: string;
  display_name: string;
  role: Role;
  temporary_password?: string;
  enabled: boolean;
  mfa_required: boolean;
  application_ids: string[];
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
  launchApp: (id: string) => request<{ launch_url: string }>(`/api/apps/${id}/launch`),
  adminApps: () => request<PortalApplication[]>("/api/admin/applications"),
  users: (params: URLSearchParams) => request<UserListResponse>(`/api/admin/users?${params.toString()}`),
  user: (id: string) => request<ManagedUser>(`/api/admin/users/${id}`),
  createUser: (payload: UserPayload) =>
    request<ManagedUser>("/api/admin/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateUser: (id: string, payload: UserPayload) =>
    request<ManagedUser>(`/api/admin/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteUser: (id: string) => request<void>(`/api/admin/users/${id}`, { method: "DELETE" }),
  resetPassword: (id: string, temporary_password: string, force_password_change: boolean) =>
    request<ManagedUser>(`/api/admin/users/${id}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ temporary_password, force_password_change }),
    }),
  resetMfa: (id: string) => request<ManagedUser>(`/api/admin/users/${id}/reset-mfa`, { method: "POST" }),
};
