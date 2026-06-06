import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../services/api";
import ErrorMessage from "../components/ErrorMessage";
import styles from "./Auth.module.css";

// Login form. On success the JWT is stored (inside api.login) and we
// redirect to the home page.
export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login({ username, password });
      navigate("/home", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.logo}>MovieRec</div>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h1 className={styles.heading}>Sign In</h1>
        <p className={styles.sub}>Log in to get your recommendations.</p>

        <ErrorMessage message={error} />

        <label className={styles.label}>
          Username
          <input
            className={styles.input}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>

        <label className={styles.label}>
          Password
          <input
            className={styles.input}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        <button className={styles.submit} type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign In"}
        </button>

        <p className={styles.switch}>
          No account? <Link to="/register">Create one</Link>
        </p>
      </form>
    </div>
  );
}
