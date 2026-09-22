import { FormEvent, useEffect, useState, type ReactNode } from "react";
import { Mail, ShieldCheck } from "lucide-react";
import { api } from "../api";
import { Logo, usePageMeta } from "./chrome";
import { signInPath } from "./routes";

type MfaPrompt = {
  masked_email: string;
  expires_at: string;
  resend_available_at: string | null;
  return_to: string | null;
};

type SignInProps = {
  identifier: string;
  setIdentifier: (value: string) => void;
  password: string;
  setPassword: (value: string) => void;
  mfaCode: string;
  setMfaCode: (value: string) => void;
  mfaPrompt: MfaPrompt | null;
  error: string;
  isLoggingIn: boolean;
  hasReturnTo: boolean;
  onLogin: (event: FormEvent) => void;
  onVerify: (event: FormEvent) => void;
  onResend: () => void;
  onCancel: () => void;
};

export function SignInScreen(props: SignInProps) {
  const [notice, setNotice] = useState("");
  usePageMeta("Sign In — Blue Ash Digital", "Sign in to an existing Blue Ash Digital development or testing account.", "/signin");
  useSiteBody();
  useEffect(() => {
    const stored = sessionStorage.getItem("blueash-auth-notice");
    if (!stored) return;
    sessionStorage.removeItem("blueash-auth-notice");
    setNotice(stored);
  }, []);

  return (
    <AuthLayout>
      <section className="auth-card" aria-label="Sign in">
        {props.mfaPrompt ? (
          <form onSubmit={props.onVerify}>
            <p className="eyebrow">Email verification</p>
            <h1>Check your email</h1>
            <p className="auth-lead">Code sent to {props.mfaPrompt.masked_email}. It expires at {formatDate(props.mfaPrompt.expires_at)}.</p>
            <label>
              Verification code
              <input
                value={props.mfaCode}
                onChange={(event) => props.setMfaCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="\d{6}"
                required
              />
            </label>
            {props.error ? <div className="form-error" role="alert">{props.error}</div> : null}
            <button className="btn btn-accent" type="submit"><ShieldCheck size={18} aria-hidden="true" /> Verify</button>
            <div className="auth-links">
              <button className="text-button" type="button" onClick={props.onResend}>Resend code</button>
              <button className="text-button" type="button" onClick={props.onCancel}>Cancel</button>
            </div>
          </form>
        ) : (
          <form className={props.isLoggingIn ? "is-processing" : undefined} onSubmit={props.onLogin} aria-busy={props.isLoggingIn}>
            <p className="eyebrow">{props.hasReturnTo ? "Continue" : "Continue to Blue Ash Reel"}</p>
            <h1>Welcome back</h1>
            <p className="auth-lead">{props.hasReturnTo ? "Sign in to continue to your application." : "Sign in to an existing development or testing account."}</p>
            <label>
              Username or email
              <input value={props.identifier} onChange={(event) => props.setIdentifier(event.target.value)} autoComplete="username" disabled={props.isLoggingIn} required />
            </label>
            <label>
              Password
              <input value={props.password} onChange={(event) => props.setPassword(event.target.value)} type="password" autoComplete="current-password" disabled={props.isLoggingIn} required />
            </label>
            <div className="auth-links">
              <a href={`/forgot-password${window.location.search}`}>Forgot password?</a>
            </div>
            {props.error || notice ? <div className="form-error" role="alert">{props.error || notice}</div> : null}
            <button className="btn btn-accent" type="submit" disabled={props.isLoggingIn}>
              {props.isLoggingIn ? <span className="login-spinner" aria-hidden="true" /> : null}
              {props.isLoggingIn ? "Signing in..." : "Sign In"}
            </button>
            {props.isLoggingIn ? <div className="login-status" role="status" aria-live="polite">Signing you in and preparing your verification code...</div> : null}
            <p className="auth-account">Need an account? <a href="/support">Request development access</a></p>
            <p className="auth-note">Only essential account and connection information is used.</p>
          </form>
        )}
      </section>
    </AuthLayout>
  );
}

export function ForgotPasswordScreen() {
  usePageMeta("Forgot Password — Blue Ash Digital", "Request a password reset link for a Blue Ash Digital account.", "/forgot-password");
  useSiteBody();
  const [identifier, setIdentifier] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const result = await api.requestPasswordReset(identifier);
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to request password reset.");
    }
  }

  return (
    <AuthLayout>
      <section className="auth-card" aria-label="Forgot password">
        <form onSubmit={submit}>
          <p className="eyebrow">Account help</p>
          <h1>Password reset</h1>
          <p className="auth-lead">Enter the username or email for an existing account.</p>
          <label>
            Username or email
            <input value={identifier} onChange={(event) => setIdentifier(event.target.value)} autoComplete="username" required />
          </label>
          {message ? <div className="success-banner" role="status">{message}</div> : null}
          {error ? <div className="form-error" role="alert">{error}</div> : null}
          <button className="btn btn-accent" type="submit"><Mail size={18} aria-hidden="true" /> Send reset link</button>
          <p className="auth-account"><a href={signInPath(window.location.search)}>Back to sign in</a></p>
        </form>
      </section>
    </AuthLayout>
  );
}

export function ResetPasswordScreen() {
  usePageMeta("Reset Password — Blue Ash Digital", "Choose a new password for a Blue Ash Digital account.", "/reset-password");
  useSiteBody();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const token = new URLSearchParams(window.location.search).get("token") ?? "";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!token) {
      setError("This reset link is missing its token. Request a new password reset.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    try {
      const result = await api.completePasswordReset(token, password);
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset password.");
    }
  }

  return (
    <AuthLayout>
      <section className="auth-card" aria-label="Reset password">
        <form onSubmit={submit}>
          <p className="eyebrow">Account help</p>
          <h1>Set a new password</h1>
          <p className="auth-lead">Choose a new password for your portal account.</p>
          <label>
            New password
            <input value={password} type="password" autoComplete="new-password" onChange={(event) => setPassword(event.target.value)} required minLength={12} />
          </label>
          <label>
            Confirm password
            <input value={confirm} type="password" autoComplete="new-password" onChange={(event) => setConfirm(event.target.value)} required minLength={12} />
          </label>
          {!token ? <div className="form-error" role="alert">This reset link is missing its token. Request a new password reset.</div> : null}
          {message ? <div className="success-banner" role="status">{message}</div> : null}
          {error ? <div className="form-error" role="alert">{error}</div> : null}
          <button className="btn btn-accent" type="submit" disabled={!token}>Reset password</button>
          <p className="auth-account"><a href="/signin">Back to sign in</a></p>
        </form>
      </section>
    </AuthLayout>
  );
}

function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="site auth-layout">
      <a className="skip" href="#auth-card">Skip to sign in</a>
      <section className="auth-brand">
        <Logo surface="dark" />
        <img src="/brand/signin-tree.png" alt="" />
        <div className="auth-statement">
          <p>Your digital life should remain yours.</p>
          <p>Privacy and ownership belong in the foundation—not behind a setting.</p>
        </div>
      </section>
      <div className="auth-stage" id="auth-card">{children}</div>
    </div>
  );
}

function useSiteBody() {
  useEffect(() => {
    document.body.classList.add("site-body");
    return () => document.body.classList.remove("site-body");
  }, []);
}

function formatDate(value: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
