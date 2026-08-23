import { useEffect, useMemo, useState } from "react";
import { Activity, AppWindow, CheckCircle2, KeyRound, LockKeyhole, LogOut, Mail, Pencil, Plus, Search, Settings, ShieldCheck, Trash2, UserRoundCog } from "lucide-react";
import { api, CurrentUser, EmailSettings, EmailSettingsPayload, ManagedUser, PermissionRead, PortalApplication, Role, RoleRead, UserPayload } from "./api";

type View = "dashboard" | "applications" | "admin-users" | "admin-apps" | "admin-audit" | "admin-settings" | "profile";
type PublicMode = "login" | "forgot-password" | "reset-password";
type UserDraft = {
  id?: string;
  username: string;
  email: string;
  display_name: string;
  role: Role;
  temporary_password: string;
  confirm_password: string;
  enabled: boolean;
  mfa_required: boolean;
  application_ids: string[];
};

const blankUser: UserDraft = {
  username: "",
  email: "",
  display_name: "",
  role: "USER",
  temporary_password: "",
  confirm_password: "",
  enabled: true,
  mfa_required: false,
  application_ids: [],
};

export function App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [apps, setApps] = useState<PortalApplication[]>([]);
  const [view, setView] = useState<View>("dashboard");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [publicMode, setPublicMode] = useState<PublicMode>(() => window.location.pathname.includes("reset-password") ? "reset-password" : window.location.pathname.includes("forgot-password") ? "forgot-password" : "login");

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    if (!can(user, viewPermission(view))) setView("dashboard");
    api.apps().then(setApps).catch(() => setApps([]));
  }, [user, view]);

  const categories = useMemo(() => ["All", ...Array.from(new Set(apps.map((app) => app.category))).sort()], [apps]);
  const filteredApps = useMemo(() => {
    return apps.filter((app) => {
      const matchesCategory = category === "All" || app.category === category;
      const text = `${app.name} ${app.description} ${app.category}`.toLowerCase();
      return matchesCategory && text.includes(query.toLowerCase());
    });
  }, [apps, category, query]);

  async function handleLogin(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const currentUser = await api.login(identifier, password);
      setUser(currentUser);
      setPassword("");
      setView("dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid username/email or password.");
    }
  }

  async function handleLogout() {
    await api.logout().catch(() => undefined);
    setUser(null);
    setApps([]);
    setIdentifier("");
    setPassword("");
  }

  async function launchApplication(app: PortalApplication) {
    setError("");
    try {
      const result = await api.launchApp(app.id);
      window.open(result.launch_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "You do not have access to that application.");
    }
  }

  if (loading) return <main className="boot-screen">Blue Ash Digital</main>;

  if (!user) {
    if (publicMode === "forgot-password") return <ForgotPassword onBack={() => setPublicMode("login")} />;
    if (publicMode === "reset-password") return <ResetPassword onBack={() => setPublicMode("login")} />;
    return (
      <main className="public-shell">
        <section className="login-panel" aria-label="Sign in">
          <div className="brand-mark"><span>BA</span></div>
          <h1>Blue Ash Digital</h1>
          <p>Custom Applications Portal</p>
          <form onSubmit={handleLogin}>
            <label>Username or Email<input value={identifier} onChange={(event) => setIdentifier(event.target.value)} autoComplete="username" required /></label>
            <label>Password<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" required /></label>
            {error ? <div className="form-error">{error}</div> : null}
            <button className="primary-action" type="submit"><LockKeyhole size={18} />Sign In</button>
          </form>
          <button className="quiet-button" type="button" onClick={() => setPublicMode("forgot-password")}>Forgot Password?</button>
        </section>
      </main>
    );
  }

  const showAdminSection = can(user, "users.view") || can(user, "applications_admin.view") || can(user, "audit.view") || can(user, "settings.view");

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark small">BA</div>
          <div><strong>Blue Ash</strong><span>Digital Portal</span></div>
        </div>
        <nav>
          {can(user, "dashboard.view") ? <button className={view === "dashboard" ? "active" : ""} onClick={() => setView("dashboard")}><AppWindow size={18} /> Dashboard</button> : null}
          {can(user, "applications.view") ? <button className={view === "applications" ? "active" : ""} onClick={() => setView("applications")}><ShieldCheck size={18} /> Applications</button> : null}
          {showAdminSection ? (
            <>
              <span className="nav-section">Administration</span>
              {can(user, "users.view") ? <button className={view === "admin-users" ? "active" : ""} onClick={() => setView("admin-users")}><UserRoundCog size={18} /> Users</button> : null}
              {can(user, "applications_admin.view") ? <button className={view === "admin-apps" ? "active" : ""} onClick={() => setView("admin-apps")}><ShieldCheck size={18} /> Applications</button> : null}
              {can(user, "audit.view") ? <button className={view === "admin-audit" ? "active" : ""} onClick={() => setView("admin-audit")}><Activity size={18} /> Audit Log</button> : null}
              {can(user, "settings.view") ? <button className={view === "admin-settings" ? "active" : ""} onClick={() => setView("admin-settings")}><Settings size={18} /> Settings</button> : null}
            </>
          ) : null}
        </nav>
        <div className="sidebar-footer">
          <button onClick={() => setView("profile")}>{user.display_name}</button>
          <button onClick={handleLogout}><LogOut size={18} /> Logout</button>
        </div>
      </aside>

      <section className="content">
        {error ? <div className="form-error page-error">{error}</div> : null}
        {view === "dashboard" || view === "applications" ? (
          <ApplicationDashboard apps={filteredApps} categories={categories} category={category} query={query} setCategory={setCategory} setQuery={setQuery} user={user} launchApplication={launchApplication} />
        ) : view === "admin-users" && can(user, "users.view") ? (
          <UsersAdmin currentUser={user} />
        ) : view === "admin-settings" && can(user, "settings.view") ? (
          <SettingsAdmin user={user} />
        ) : view === "profile" ? (
          <Profile user={user} />
        ) : can(user, viewPermission(view)) ? (
          <Placeholder view={view} />
        ) : (
          <Unauthorized />
        )}
      </section>
    </main>
  );
}

function can(user: CurrentUser, permission: string) {
  return user.permissions.includes(permission);
}

function viewPermission(view: View) {
  const permissions: Record<View, string> = {
    dashboard: "dashboard.view",
    applications: "applications.view",
    "admin-users": "users.view",
    "admin-apps": "applications_admin.view",
    "admin-audit": "audit.view",
    "admin-settings": "settings.view",
    profile: "profile.manage",
  };
  return permissions[view];
}

function ForgotPassword({ onBack }: { onBack: () => void }) {
  const [identifier, setIdentifier] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const result = await api.requestPasswordReset(identifier);
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to request password reset.");
    }
  }
  return <main className="public-shell"><section className="login-panel" aria-label="Forgot password"><div className="brand-mark"><span>BA</span></div><h1>Password Reset</h1><p>Enter your username or email.</p><form onSubmit={submit}><label>Username or Email<input value={identifier} onChange={(event) => setIdentifier(event.target.value)} required /></label>{message ? <div className="success-banner">{message}</div> : null}{error ? <div className="form-error">{error}</div> : null}<button className="primary-action" type="submit"><Mail size={18} /> Send Reset Link</button></form><button className="quiet-button" type="button" onClick={onBack}>Back to Sign In</button></section></main>;
}

function ResetPassword({ onBack }: { onBack: () => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const token = new URLSearchParams(window.location.search).get("token") ?? "";
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    if (password !== confirm) return setError("Passwords do not match.");
    try {
      const result = await api.completePasswordReset(token, password);
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset password.");
    }
  }
  return <main className="public-shell"><section className="login-panel" aria-label="Reset password"><div className="brand-mark"><span>BA</span></div><h1>Set Password</h1><p>Choose a new portal password.</p><form onSubmit={submit}><label>New Password<input value={password} type="password" onChange={(event) => setPassword(event.target.value)} required minLength={12} /></label><label>Confirm Password<input value={confirm} type="password" onChange={(event) => setConfirm(event.target.value)} required minLength={12} /></label>{message ? <div className="success-banner">{message}</div> : null}{error ? <div className="form-error">{error}</div> : null}<button className="primary-action" type="submit"><KeyRound size={18} /> Reset Password</button></form><button className="quiet-button" type="button" onClick={onBack}>Back to Sign In</button></section></main>;
}

function ApplicationDashboard({ apps, categories, category, query, setCategory, setQuery, user, launchApplication }: { apps: PortalApplication[]; categories: string[]; category: string; query: string; setCategory: (value: string) => void; setQuery: (value: string) => void; user: CurrentUser; launchApplication: (app: PortalApplication) => void }) {
  return (
    <>
      <header className="content-header">
        <div><span className="eyebrow">Application Dashboard</span><h2>Welcome, {user.display_name}</h2></div>
        <div className="search-box"><Search size={18} /><input placeholder="Search applications" value={query} onChange={(event) => setQuery(event.target.value)} /></div>
      </header>
      <div className="category-tabs">
        {categories.map((item) => <button key={item} className={item === category ? "selected" : ""} onClick={() => setCategory(item)}>{item}</button>)}
      </div>
      <div className="app-grid">
        {apps.map((app) => (
          <article className="app-card" key={app.id}>
            <div className="app-icon">{app.icon || "APP"}</div>
            <div><h3>{app.name}</h3><p>{app.description}</p></div>
            <div className="card-meta"><span>{app.category}</span><span className={`status ${app.status.toLowerCase()}`}>{app.status}</span></div>
            <button className="launch-button" onClick={() => launchApplication(app)}>Launch</button>
          </article>
        ))}
      </div>
    </>
  );
}

function UsersAdmin({ currentUser }: { currentUser: CurrentUser }) {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [applications, setApplications] = useState<PortalApplication[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [enabled, setEnabled] = useState("");
  const [draft, setDraft] = useState<UserDraft | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const limit = 25;

  useEffect(() => { api.adminApps().then(setApplications).catch(() => setApplications([])); }, []);
  useEffect(() => { loadUsers(); }, [offset, role, enabled]);

  async function loadUsers(nextSearch = search) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (nextSearch.trim()) params.set("search", nextSearch.trim());
    if (role) params.set("role", role);
    if (enabled) params.set("enabled", enabled);
    try {
      const result = await api.users(params);
      setUsers(result.items);
      setTotal(result.total);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load users.");
    }
  }

  function beginEdit(selected: ManagedUser) {
    setDraft({ id: selected.id, username: selected.username, email: selected.email, display_name: selected.display_name, role: selected.role, temporary_password: "", confirm_password: "", enabled: selected.enabled, mfa_required: selected.mfa_required, application_ids: selected.application_ids });
  }

  async function saveUser() {
    if (!draft) return;
    setError("");
    if (!draft.id && draft.temporary_password !== draft.confirm_password) return setError("Temporary passwords do not match.");
    if (!draft.id && draft.temporary_password.length < 12) return setError("Temporary password must be at least 12 characters.");
    const payload: UserPayload = {
      username: draft.username,
      email: draft.email,
      display_name: draft.display_name,
      role: draft.role,
      temporary_password: draft.temporary_password,
      enabled: draft.enabled,
      mfa_required: draft.mfa_required,
      application_ids: draft.role === "ADMINISTRATOR" ? [] : draft.application_ids,
    };
    try {
      if (draft.id) {
        await api.updateUser(draft.id, payload);
        setMessage("User updated.");
      } else {
        await api.createUser(payload);
        setMessage("User created.");
      }
      setDraft(null);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save user.");
    }
  }

  async function deleteUser(selected: ManagedUser) {
    if (!window.confirm(`Delete user "${selected.username}"?\n\nThis will permanently remove this user and their application assignments.`)) return;
    try {
      await api.deleteUser(selected.id);
      setMessage("User deleted.");
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete user.");
    }
  }

  async function resetPassword(selected: ManagedUser) {
    const newPassword = window.prompt(`Enter a new temporary password for ${selected.username}.`);
    if (!newPassword) return;
    if (newPassword.length < 12) return setError("Temporary password must be at least 12 characters.");
    try {
      await api.resetPassword(selected.id, newPassword, false);
      setMessage("Password reset.");
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset password.");
    }
  }

  async function resetMfa(selected: ManagedUser) {
    if (!window.confirm(`Reset MFA for "${selected.username}"?`)) return;
    try {
      await api.resetMfa(selected.id);
      setMessage("MFA reset.");
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset MFA.");
    }
  }

  return (
    <>
      <header className="content-header">
        <div><span className="eyebrow">Administration</span><h2>User Administration</h2></div>
        <button className="primary-action compact" onClick={() => setDraft(blankUser)}><Plus size={18} /> Add User</button>
      </header>
      <div className="admin-toolbar">
        <div className="search-box"><Search size={18} /><input placeholder="Search users" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { setOffset(0); loadUsers(search); } }} /></div>
        <select value={role} onChange={(event) => { setRole(event.target.value); setOffset(0); }}><option value="">All roles</option><option value="ADMINISTRATOR">Admin</option><option value="USER">User</option></select>
        <select value={enabled} onChange={(event) => { setEnabled(event.target.value); setOffset(0); }}><option value="">All statuses</option><option value="true">Enabled</option><option value="false">Disabled</option></select>
        <button className="secondary-action" onClick={() => { setOffset(0); loadUsers(search); }}>Apply</button>
      </div>
      {message ? <div className="success-banner">{message}</div> : null}
      {error ? <div className="form-error">{error}</div> : null}
      <div className="table-shell">
        <table>
          <thead><tr><th>Username</th><th>Display Name</th><th>Email</th><th>Role</th><th>Status</th><th>MFA</th><th>Last Login</th><th>Apps</th><th>Actions</th></tr></thead>
          <tbody>
            {users.map((item) => (
              <tr key={item.id}>
                <td>{item.username}</td><td>{item.display_name}</td><td>{item.email}</td><td>{item.role === "ADMINISTRATOR" ? "Admin" : "User"}</td>
                <td><span className={`pill ${item.enabled ? "good" : "bad"}`}>{item.enabled ? "Enabled" : "Disabled"}</span></td>
                <td>{item.mfa_enabled ? "Configured" : item.mfa_required ? "Required" : "Off"}</td><td>{formatDate(item.last_login_at)}</td><td>{item.role === "ADMINISTRATOR" ? "All" : item.applications_assigned}</td>
                <td><div className="action-row"><button title="Edit" onClick={() => beginEdit(item)}><Pencil size={16} /></button><button title="Reset password" onClick={() => resetPassword(item)}><KeyRound size={16} /></button><button title="Reset MFA" onClick={() => resetMfa(item)}><ShieldCheck size={16} /></button><button title="Delete" disabled={item.id === currentUser.id} onClick={() => deleteUser(item)}><Trash2 size={16} /></button></div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination"><span>{total ? `${offset + 1}-${Math.min(offset + limit, total)} of ${total}` : "0 users"}</span><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</button><button disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>Next</button></div>
      {draft ? <UserModal draft={draft} setDraft={setDraft} applications={applications} onCancel={() => setDraft(null)} onSave={saveUser} /> : null}
    </>
  );
}

function UserModal({ draft, setDraft, applications, onCancel, onSave }: { draft: UserDraft; setDraft: (draft: UserDraft) => void; applications: PortalApplication[]; onCancel: () => void; onSave: () => void }) {
  const isEdit = Boolean(draft.id);
  const selected = new Set(draft.application_ids);
  function toggleApp(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setDraft({ ...draft, application_ids: Array.from(next) });
  }
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <section className="modal-panel">
        <header><span className="eyebrow">{isEdit ? "Edit User" : "Add User"}</span><h3>{isEdit ? draft.username : "New User"}</h3></header>
        <div className="form-grid">
          <label>Username<input value={draft.username} disabled={isEdit} onChange={(event) => setDraft({ ...draft, username: event.target.value })} required /></label>
          <label>Display Name<input value={draft.display_name} onChange={(event) => setDraft({ ...draft, display_name: event.target.value })} required /></label>
          <label>Email<input value={draft.email} type="email" onChange={(event) => setDraft({ ...draft, email: event.target.value })} required /></label>
          <label>Role<select value={draft.role} onChange={(event) => setDraft({ ...draft, role: event.target.value as Role })}><option value="USER">User</option><option value="ADMINISTRATOR">Admin</option></select></label>
          {!isEdit ? <><label>Temporary Password<input value={draft.temporary_password} type="password" onChange={(event) => setDraft({ ...draft, temporary_password: event.target.value })} required /></label><label>Confirm Temporary Password<input value={draft.confirm_password} type="password" onChange={(event) => setDraft({ ...draft, confirm_password: event.target.value })} required /></label></> : null}
        </div>
        <div className="toggle-row"><label><input type="checkbox" checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} /> Enabled</label><label><input type="checkbox" checked={draft.mfa_required} onChange={(event) => setDraft({ ...draft, mfa_required: event.target.checked })} /> Require MFA</label></div>
        <section className="assignment-panel">
          <h4>Application Access</h4>
          {draft.role === "ADMINISTRATOR" ? <p>Administrators automatically have access to all applications.</p> : <div className="assignment-grid">{applications.map((app) => <label key={app.id}><input type="checkbox" checked={selected.has(app.id)} onChange={() => toggleApp(app.id)} /><span>{app.name}</span></label>)}</div>}
        </section>
        <footer className="modal-actions"><button className="secondary-action" onClick={onCancel}>Cancel</button><button className="primary-action compact" onClick={onSave}>Save</button></footer>
      </section>
    </div>
  );
}

function SettingsAdmin({ user }: { user: CurrentUser }) {
  const [tab, setTab] = useState<"roles" | "email" | "general" | "auth">("roles");
  return (
    <>
      <header className="content-header">
        <div><span className="eyebrow">Administration</span><h2>Settings</h2></div>
      </header>
      <div className="settings-tabs">
        {can(user, "roles.view") ? <button className={tab === "roles" ? "selected" : ""} onClick={() => setTab("roles")}><ShieldCheck size={16} /> Roles & Permissions</button> : null}
        {can(user, "email_settings.view") ? <button className={tab === "email" ? "selected" : ""} onClick={() => setTab("email")}><Mail size={16} /> Email</button> : null}
        <button className={tab === "general" ? "selected" : ""} onClick={() => setTab("general")}><Settings size={16} /> General</button>
        <button className={tab === "auth" ? "selected" : ""} onClick={() => setTab("auth")}><LockKeyhole size={16} /> Authentication</button>
      </div>
      {tab === "roles" && can(user, "roles.view") ? <RolesSettings canEdit={can(user, "roles.edit")} /> : null}
      {tab === "email" && can(user, "email_settings.view") ? <EmailSettingsPanel canEdit={can(user, "email_settings.edit")} canTest={can(user, "email_settings.test")} currentUser={user} /> : null}
      {tab === "general" ? <div className="admin-surface"><span className="eyebrow">General</span><h3>Portal</h3><p>Portal name and domain are managed through deployment environment configuration.</p></div> : null}
      {tab === "auth" ? <div className="admin-surface"><span className="eyebrow">Authentication</span><h3>Session Policy</h3><p>Sessions, secure cookies, MFA requirements, and password resets use the configured backend authentication settings.</p></div> : null}
    </>
  );
}

function RolesSettings({ canEdit }: { canEdit: boolean }) {
  const [roles, setRoles] = useState<RoleRead[]>([]);
  const [permissions, setPermissions] = useState<PermissionRead[]>([]);
  const [critical, setCritical] = useState<string[]>([]);
  const [selectedKey, setSelectedKey] = useState<Role>("ADMINISTRATOR");
  const [draft, setDraft] = useState<Set<string>>(new Set());
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { loadRoles(); }, []);

  async function loadRoles(nextSelected?: Role) {
    try {
      const result = await api.roles();
      setRoles(result.roles);
      setPermissions(result.permissions);
      setCritical(result.critical_permissions);
      const key = nextSelected ?? selectedKey;
      const selected = result.roles.find((role) => role.key === key) ?? result.roles[0];
      if (selected) {
        setSelectedKey(selected.key);
        setDraft(new Set(selected.permission_keys));
      }
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load roles.");
    }
  }

  const selectedRole = roles.find((role) => role.key === selectedKey);
  const grouped = permissions.reduce<Record<string, PermissionRead[]>>((acc, permission) => {
    acc[permission.group] = [...(acc[permission.group] ?? []), permission];
    return acc;
  }, {});

  function chooseRole(role: RoleRead) {
    setSelectedKey(role.key);
    setDraft(new Set(role.permission_keys));
    setMessage("");
    setError("");
  }

  function togglePermission(key: string) {
    const next = new Set(draft);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setDraft(next);
  }

  async function save() {
    if (!selectedRole) return;
    try {
      const updated = await api.updateRole(selectedRole.key, Array.from(draft));
      setMessage("Role permissions updated.");
      await loadRoles(updated.key);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save role permissions.");
    }
  }

  return (
    <div className="settings-layout">
      <section className="admin-surface">
        <div className="section-title"><span className="eyebrow">Roles</span><h3>Permission Groups</h3></div>
        <div className="table-shell compact-table">
          <table>
            <thead><tr><th>Role</th><th>Users</th><th>Type</th></tr></thead>
            <tbody>{roles.map((role) => <tr key={role.key} className={role.key === selectedKey ? "selected-row" : ""} onClick={() => chooseRole(role)}><td>{role.name}</td><td>{role.users_count}</td><td>{role.system ? "System" : "Custom"}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
      <section className="admin-surface permission-editor">
        <div className="section-title"><span className="eyebrow">{selectedRole?.system ? "System Role" : "Role"}</span><h3>{selectedRole?.name ?? "Role"}</h3><p>{selectedRole?.description}</p></div>
        {message ? <div className="success-banner">{message}</div> : null}
        {error ? <div className="form-error">{error}</div> : null}
        {Object.entries(grouped).map(([group, items]) => (
          <div className="permission-group" key={group}>
            <h4>{group}</h4>
            <div className="permission-list">
              {items.map((permission) => {
                const protectedAdmin = selectedRole?.key === "ADMINISTRATOR" && critical.includes(permission.key);
                return <label key={permission.key}><input type="checkbox" checked={draft.has(permission.key)} disabled={!canEdit || protectedAdmin} onChange={() => togglePermission(permission.key)} /><span>{permission.label}</span></label>;
              })}
            </div>
          </div>
        ))}
        <footer className="modal-actions"><button className="primary-action compact" disabled={!canEdit} onClick={save}><CheckCircle2 size={16} /> Save Permissions</button></footer>
      </section>
    </div>
  );
}

function EmailSettingsPanel({ canEdit, canTest, currentUser }: { canEdit: boolean; canTest: boolean; currentUser: CurrentUser }) {
  const [settings, setSettings] = useState<EmailSettings | null>(null);
  const [draft, setDraft] = useState<EmailSettingsPayload>({ provider: "gmail", email_address: "", app_password: "", from_name: "Application Portal", reply_to: "", enabled: false });
  const [replacePassword, setReplacePassword] = useState(false);
  const [recipient, setRecipient] = useState(currentUser.email);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { loadEmail(); }, []);

  async function loadEmail() {
    try {
      const result = await api.emailSettings();
      setSettings(result);
      setDraft({ provider: "gmail", email_address: result.email_address ?? "", app_password: "", from_name: result.from_name ?? "Application Portal", reply_to: result.reply_to ?? "", enabled: result.enabled });
      setRecipient(result.reply_to ?? result.email_address ?? currentUser.email);
      setReplacePassword(!result.has_app_password);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load email settings.");
    }
  }

  async function save() {
    try {
      const payload: EmailSettingsPayload = { ...draft, reply_to: draft.reply_to || null };
      if (!replacePassword || !draft.app_password) delete payload.app_password;
      const result = await api.updateEmailSettings(payload);
      setSettings(result);
      setReplacePassword(!result.has_app_password);
      setDraft({ ...draft, app_password: "" });
      setMessage("Email settings saved.");
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save email settings.");
    }
  }

  async function test() {
    try {
      const result = await api.testEmail(recipient);
      setMessage(result.message);
      setError("");
      await loadEmail();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send test email.");
    }
  }

  return (
    <div className="settings-layout">
      <section className="admin-surface">
        <div className="section-title"><span className="eyebrow">Email</span><h3>Outgoing Provider</h3></div>
        {message ? <div className="success-banner">{message}</div> : null}
        {error ? <div className="form-error">{error}</div> : null}
        <div className="form-grid">
          <label>Provider<select value={draft.provider} disabled={!canEdit} onChange={(event) => setDraft({ ...draft, provider: event.target.value as "gmail" })}><option value="gmail">Gmail</option></select></label>
          <label>Email Address<input value={draft.email_address} disabled={!canEdit} type="email" onChange={(event) => setDraft({ ...draft, email_address: event.target.value })} /></label>
          <label>From Name<input value={draft.from_name} disabled={!canEdit} onChange={(event) => setDraft({ ...draft, from_name: event.target.value })} /></label>
          <label>Reply-To Address<input value={draft.reply_to ?? ""} disabled={!canEdit} type="email" onChange={(event) => setDraft({ ...draft, reply_to: event.target.value })} /></label>
        </div>
        <div className="static-settings"><span>SMTP Host: smtp.gmail.com</span><span>Port: 587</span><span>Encryption: STARTTLS</span></div>
        <div className="toggle-row"><label><input type="checkbox" checked={draft.enabled} disabled={!canEdit} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} /> Enable Email</label></div>
        <section className="assignment-panel">
          <h4>Gmail App Password</h4>
          {settings?.has_app_password && !replacePassword ? <div className="secret-row"><span>••••••••••••••••</span><button className="secondary-action" disabled={!canEdit} onClick={() => setReplacePassword(true)}>Replace Password</button></div> : <label>App Password<input value={draft.app_password ?? ""} disabled={!canEdit} type="password" onChange={(event) => setDraft({ ...draft, app_password: event.target.value })} /></label>}
        </section>
        <footer className="modal-actions"><button className="primary-action compact" disabled={!canEdit} onClick={save}><CheckCircle2 size={16} /> Save Email Settings</button></footer>
      </section>
      <section className="admin-surface">
        <div className="section-title"><span className="eyebrow">Status</span><h3>{settings?.status ?? "NOT_CONFIGURED"}</h3></div>
        <p>Provider: Gmail</p>
        <p>Last Test: {formatDate(settings?.last_test_at ?? null)}</p>
        <p>Result: {settings?.last_test_result ?? "Never tested"}</p>
        {settings?.last_error ? <div className="form-error">{settings.last_error}</div> : null}
        <div className="form-grid single">
          <label>Test Recipient<input value={recipient} disabled={!canTest} type="email" onChange={(event) => setRecipient(event.target.value)} /></label>
        </div>
        <button className="secondary-action" disabled={!canTest} onClick={test}><Mail size={16} /> Send Test Email</button>
        <section className="help-panel">
          <h4>Gmail setup</h4>
          <p>Gmail requires an App Password, not your normal Google password. Enable 2-Step Verification in the Google account, create an App Password, then enter that generated value here.</p>
        </section>
      </section>
    </div>
  );
}

function Profile({ user }: { user: CurrentUser }) {
  return <div className="admin-surface"><span className="eyebrow">Profile</span><h2>{user.display_name}</h2><p>{user.email}</p><p>{user.role === "ADMINISTRATOR" ? "Admin" : "User"}</p></div>;
}

function Unauthorized() {
  return <div className="admin-surface"><span className="eyebrow">403 Forbidden</span><h2>Unauthorized</h2><p>You do not have access to this section.</p></div>;
}

function Placeholder({ view }: { view: View }) {
  const labels: Record<View, string> = { dashboard: "Dashboard", applications: "Applications", "admin-users": "User Administration", "admin-apps": "Application Administration", "admin-audit": "Audit Log", "admin-settings": "Settings", profile: "Profile" };
  return <div className="admin-surface"><span className="eyebrow">{labels[view]}</span><h2>{labels[view]}</h2><p>This section is available to administrators.</p></div>;
}

function formatDate(value: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
