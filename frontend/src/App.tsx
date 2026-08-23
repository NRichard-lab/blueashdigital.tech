import { useEffect, useMemo, useState } from "react";
import { Activity, AppWindow, LockKeyhole, LogOut, Search, ShieldCheck, UserRoundCog } from "lucide-react";
import { api, CurrentUser, PortalApplication } from "./api";

type View = "dashboard" | "admin-users" | "admin-apps" | "admin-audit" | "profile";

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
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    api.apps().then(setApps).catch(() => setApps([]));
  }, [user]);

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

  if (loading) {
    return <main className="boot-screen">Blue Ash Digital</main>;
  }

  if (!user) {
    return (
      <main className="public-shell">
        <section className="login-panel" aria-label="Sign in">
          <div className="brand-mark">
            <span>BA</span>
          </div>
          <h1>Blue Ash Digital</h1>
          <p>Custom Applications Portal</p>
          <form onSubmit={handleLogin}>
            <label>
              Username or Email
              <input value={identifier} onChange={(event) => setIdentifier(event.target.value)} autoComplete="username" required />
            </label>
            <label>
              Password
              <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" required />
            </label>
            {error ? <div className="form-error">{error}</div> : null}
            <button className="primary-action" type="submit">
              <LockKeyhole size={18} />
              Sign In
            </button>
          </form>
          <a className="quiet-link" href="/forgot-password">Forgot Password?</a>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark small">BA</div>
          <div>
            <strong>Blue Ash</strong>
            <span>Digital Portal</span>
          </div>
        </div>
        <nav>
          <button className={view === "dashboard" ? "active" : ""} onClick={() => setView("dashboard")}>
            <AppWindow size={18} /> Dashboard
          </button>
          {user.role === "ADMINISTRATOR" ? (
            <>
              <span className="nav-section">Administration</span>
              <button className={view === "admin-users" ? "active" : ""} onClick={() => setView("admin-users")}>
                <UserRoundCog size={18} /> Users
              </button>
              <button className={view === "admin-apps" ? "active" : ""} onClick={() => setView("admin-apps")}>
                <ShieldCheck size={18} /> Applications
              </button>
              <button className={view === "admin-audit" ? "active" : ""} onClick={() => setView("admin-audit")}>
                <Activity size={18} /> Audit Log
              </button>
            </>
          ) : null}
        </nav>
        <div className="sidebar-footer">
          <button onClick={() => setView("profile")}>{user.display_name}</button>
          <button onClick={handleLogout}>
            <LogOut size={18} /> Logout
          </button>
        </div>
      </aside>

      <section className="content">
        {view === "dashboard" ? (
          <>
            <header className="content-header">
              <div>
                <span className="eyebrow">Application Dashboard</span>
                <h2>Welcome, {user.display_name}</h2>
              </div>
              <div className="search-box">
                <Search size={18} />
                <input placeholder="Search applications" value={query} onChange={(event) => setQuery(event.target.value)} />
              </div>
            </header>
            <div className="category-tabs">
              {categories.map((item) => (
                <button key={item} className={item === category ? "selected" : ""} onClick={() => setCategory(item)}>
                  {item}
                </button>
              ))}
            </div>
            <div className="app-grid">
              {filteredApps.map((app) => (
                <article className="app-card" key={app.id}>
                  <div className="app-icon">{app.icon || "APP"}</div>
                  <div>
                    <h3>{app.name}</h3>
                    <p>{app.description}</p>
                  </div>
                  <div className="card-meta">
                    <span>{app.category}</span>
                    <span className={`status ${app.status.toLowerCase()}`}>{app.status}</span>
                  </div>
                  <a className="launch-button" href={app.launch_url} target="_blank" rel="noreferrer">
                    Launch
                  </a>
                </article>
              ))}
            </div>
          </>
        ) : (
          <Placeholder view={view} />
        )}
      </section>
    </main>
  );
}

function Placeholder({ view }: { view: View }) {
  const labels: Record<View, string> = {
    dashboard: "Dashboard",
    "admin-users": "User Administration",
    "admin-apps": "Application Administration",
    "admin-audit": "Audit Log",
    profile: "Profile",
  };
  return (
    <div className="admin-surface">
      <span className="eyebrow">{labels[view]}</span>
      <h2>{labels[view]}</h2>
      <p>This section is backed by secured API routes and is ready for the next implementation phase.</p>
    </div>
  );
}

