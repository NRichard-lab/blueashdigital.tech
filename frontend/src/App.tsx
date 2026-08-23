import { useEffect, useMemo, useState } from "react";
import { Activity, AppWindow, KeyRound, LockKeyhole, LogOut, Pencil, Plus, Search, ShieldCheck, Trash2, UserRoundCog } from "lucide-react";
import { api, CurrentUser, ManagedUser, PortalApplication, Role, UserPayload } from "./api";

type View = "dashboard" | "applications" | "admin-users" | "admin-apps" | "admin-audit" | "profile";
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

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    if (user.role !== "ADMINISTRATOR" && view.startsWith("admin-")) setView("dashboard");
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
          <a className="quiet-link" href="/forgot-password">Forgot Password?</a>
        </section>
      </main>
    );
  }

  const isAdmin = user.role === "ADMINISTRATOR";

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark small">BA</div>
          <div><strong>Blue Ash</strong><span>Digital Portal</span></div>
        </div>
        <nav>
          <button className={view === "dashboard" ? "active" : ""} onClick={() => setView("dashboard")}><AppWindow size={18} /> Dashboard</button>
          <button className={view === "applications" ? "active" : ""} onClick={() => setView("applications")}><ShieldCheck size={18} /> Applications</button>
          {isAdmin ? (
            <>
              <span className="nav-section">Administration</span>
              <button className={view === "admin-users" ? "active" : ""} onClick={() => setView("admin-users")}><UserRoundCog size={18} /> Users</button>
              <button className={view === "admin-apps" ? "active" : ""} onClick={() => setView("admin-apps")}><ShieldCheck size={18} /> Applications</button>
              <button className={view === "admin-audit" ? "active" : ""} onClick={() => setView("admin-audit")}><Activity size={18} /> Audit Log</button>
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
        ) : view === "admin-users" && isAdmin ? (
          <UsersAdmin currentUser={user} />
        ) : view === "profile" ? (
          <Profile user={user} />
        ) : isAdmin ? (
          <Placeholder view={view} />
        ) : (
          <Unauthorized />
        )}
      </section>
    </main>
  );
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

function Profile({ user }: { user: CurrentUser }) {
  return <div className="admin-surface"><span className="eyebrow">Profile</span><h2>{user.display_name}</h2><p>{user.email}</p><p>{user.role === "ADMINISTRATOR" ? "Admin" : "User"}</p></div>;
}

function Unauthorized() {
  return <div className="admin-surface"><span className="eyebrow">403 Forbidden</span><h2>Unauthorized</h2><p>You do not have access to this section.</p></div>;
}

function Placeholder({ view }: { view: View }) {
  const labels: Record<View, string> = { dashboard: "Dashboard", applications: "Applications", "admin-users": "User Administration", "admin-apps": "Application Administration", "admin-audit": "Audit Log", profile: "Profile" };
  return <div className="admin-surface"><span className="eyebrow">{labels[view]}</span><h2>{labels[view]}</h2><p>This section is available to administrators.</p></div>;
}

function formatDate(value: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
