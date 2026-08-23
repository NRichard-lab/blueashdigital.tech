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

export type PermissionRead = {
  key: string;
  label: string;
  group: string;
  description: string;
};

export type RoleRead = {
  id: string;
  key: Role;
  name: string;
  description: string;
  system: boolean;
  users_count: number;
  permission_keys: string[];
};

export type RoleListResponse = {
  roles: RoleRead[];
  permissions: PermissionRead[];
  critical_permissions: string[];
};

export type EmailSettings = {
  provider: "gmail" | "hostinger";
  email_address: string | null;
  smtp_username: string | null;
  from_email: string | null;
  from_name: string | null;
  reply_to: string | null;
  enabled: boolean;
  status: "NOT_CONFIGURED" | "CONFIGURED" | "VERIFIED" | "ERROR";
  has_app_password: boolean;
  has_smtp_password: boolean;
  smtp_host: string;
  smtp_port: number;
  smtp_security: "SSL_TLS" | "STARTTLS";
  encryption: string;
  last_test_at: string | null;
  last_test_result: string | null;
  last_error: string | null;
};

export type EmailSettingsPayload = {
  provider: "gmail" | "hostinger";
  email_address?: string | null;
  app_password?: string;
  smtp_username?: string | null;
  smtp_password?: string;
  from_email?: string | null;
  smtp_port?: number;
  smtp_security?: "SSL_TLS" | "STARTTLS";
  from_name: string;
  reply_to?: string | null;
  enabled: boolean;
};

export type AuthenticationSettings = {
  idle_timeout_minutes: number;
  absolute_timeout_minutes: number;
  mfa_code_expiration_minutes: number;
  mfa_max_attempts: number;
  mfa_resend_delay_seconds: number;
};

export type MfaRequired = {
  status: "MFA_REQUIRED";
  masked_email: string;
  expires_at: string;
  resend_available_at: string | null;
};

export type LoginResponse =
  | { status: "AUTHENTICATED"; user: CurrentUser; masked_email?: null; expires_at?: null; resend_available_at?: null }
  | MfaRequired;

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "https://api.blueashdigital.tech";

const FIELD_LABELS: Record<string, string> = {
  email_address: "Gmail Email Address",
  smtp_username: "Mailbox Username",
  smtp_password: "SMTP Password",
  from_email: "From Address",
  from_name: "From Name",
  reply_to: "Reply-To Address",
  app_password: "App Password",
  recipient: "Test Recipient",
};

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatValidationMessage(item: unknown): string {
  if (!item || typeof item !== "object") return String(item);
  const error = item as { loc?: unknown[]; msg?: unknown; message?: unknown; detail?: unknown };
  const field = Array.isArray(error.loc) ? String(error.loc[error.loc.length - 1] ?? "") : "";
  const label = FIELD_LABELS[field] ?? titleCase(field);
  const message = typeof error.msg === "string" ? error.msg : typeof error.message === "string" ? error.message : typeof error.detail === "string" ? error.detail : "Invalid value";
  return label ? `${label}: ${message}.` : `${message}.`;
}

export function formatApiError(error: unknown, fallback = "Request failed."): string {
  if (error instanceof Error) return error.message && error.message !== "Request failed." ? error.message : fallback;
  if (typeof error === "string") return error || fallback;
  if (!error || typeof error !== "object") return fallback;
  const payload = error as { detail?: unknown; message?: unknown; error?: unknown };
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) return payload.detail.map(formatValidationMessage).join(" ");
  if (payload.detail && typeof payload.detail === "object") return formatApiError(payload.detail, fallback);
  if (typeof payload.message === "string") return payload.message;
  if (typeof payload.error === "string") return payload.error;
  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers ?? {}),
      },
      ...options,
    });
  } catch {
    throw new Error("Network request failed. Please check your connection and try again.");
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed." }));
    if (response.status === 401 && !path.startsWith("/api/auth/")) {
      window.dispatchEvent(new CustomEvent("blueash-session-expired", { detail: formatApiError(payload, "Your session has expired. Please sign in again.") }));
    }
    throw new Error(formatApiError(payload));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  login: (identifier: string, password: string) =>
    request<LoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    }),
  verifyMfa: (code: string) =>
    request<CurrentUser>("/api/auth/mfa/verify", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  resendMfa: () => request<MfaRequired>("/api/auth/mfa/resend", { method: "POST" }),
  cancelMfa: () => request<void>("/api/auth/mfa/cancel", { method: "POST" }),
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
  roles: () => request<RoleListResponse>("/api/admin/settings/roles"),
  updateRole: (roleKey: Role, permission_keys: string[]) =>
    request<RoleRead>(`/api/admin/settings/roles/${roleKey}`, {
      method: "PUT",
      body: JSON.stringify({ permission_keys }),
    }),
  emailSettings: () => request<EmailSettings>("/api/admin/settings/email"),
  updateEmailSettings: (payload: EmailSettingsPayload) =>
    request<EmailSettings>("/api/admin/settings/email", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  testEmail: (recipient: string) =>
    request<{ status: EmailSettings["status"]; message: string }>("/api/admin/settings/email/test", {
      method: "POST",
      body: JSON.stringify({ recipient }),
    }),
  authenticationSettings: () => request<AuthenticationSettings>("/api/admin/settings/authentication"),
  updateAuthenticationSettings: (payload: AuthenticationSettings) =>
    request<AuthenticationSettings>("/api/admin/settings/authentication", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  requestPasswordReset: (identifier: string) =>
    request<{ message: string }>("/api/auth/password-reset/request", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    }),
  completePasswordReset: (token: string, password: string) =>
    request<{ message: string }>("/api/auth/password-reset/complete", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),
};
