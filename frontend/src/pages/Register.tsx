import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import styles from "@/components/AuthForm.module.scss";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== passwordConfirm) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await register({
        username,
        email,
        password,
        password_confirm: passwordConfirm,
      });
      navigate("/", { replace: true });
    } catch (err: unknown) {
      setError(extractError(err) || "Could not create account.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.wrapper}>
      <form className={styles.card} onSubmit={onSubmit}>
        <h1 className={styles.title}>Create an account</h1>
        <p className={styles.subtitle}>
          Track your bar crawls and rate where you've been.
        </p>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="username">
            Username
          </label>
          <input
            id="username"
            className={styles.input}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
            minLength={3}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            className={styles.input}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            className={styles.input}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
            minLength={8}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="passwordConfirm">
            Confirm password
          </label>
          <input
            id="passwordConfirm"
            type="password"
            className={styles.input}
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            required
            autoComplete="new-password"
          />
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <button type="submit" className={styles.submit} disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </button>

        <div className={styles.footer}>
          Already have one? <Link to="/login">Sign in</Link>
        </div>
      </form>
    </div>
  );
}

function extractError(err: unknown): string | null {
  if (typeof err !== "object" || err === null) return null;
  const e = err as { response?: { data?: Record<string, unknown> } };
  const data = e.response?.data;
  if (!data) return null;

  // Flatten DRF's per-field validation error shape
  const parts: string[] = [];
  for (const [field, value] of Object.entries(data)) {
    if (Array.isArray(value)) {
      parts.push(`${field}: ${value.join(", ")}`);
    } else if (typeof value === "string") {
      parts.push(`${field}: ${value}`);
    }
  }
  return parts.length ? parts.join("\n") : null;
}
