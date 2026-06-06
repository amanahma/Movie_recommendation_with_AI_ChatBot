import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { register, login } from "../services/api";
import ErrorMessage from "../components/ErrorMessage";
import styles from "./Auth.module.css";

// Registration form. On success we auto-log-in with the same credentials
// (so the user lands straight on the home page with a valid token).
export default function RegisterPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // Confirm Password is FRONTEND-ONLY: validated here, never sent to the API.
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");           // API errors (top banner)
  const [validationError, setValidationError] = useState(""); // client-side

  // Run client-side checks before hitting the API. Returns an error string
  // if something's wrong, or "" if everything is valid.
  function validate() {
    if (!username.trim() || !email.trim() || !password || !confirmPassword) {
      return "All fields are required";
    }
    if (password.length < 8) {
      return "Password must be at least 8 characters";
    }
    if (password !== confirmPassword) {
      return "Passwords do not match";
    }
    return "";
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setValidationError("");

    // Validate first; if it fails, show the red message and do NOT call the API.
    const problem = validate();
    if (problem) {
      setValidationError(problem);
      return;
    }

    setLoading(true);
    try {
      // Note: confirmPassword is intentionally NOT included — the backend
      // only needs username, email, password.
      await register({ username, email, password });
      // Seamless: log the new user in immediately, then go home.
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
      <form className={styles.card} onSubmit={handleSubmit} noValidate>
        <h1 className={styles.heading}>Sign Up</h1>
        <p className={styles.sub}>Start getting personalized picks.</p>

        <ErrorMessage message={error} />

        <label className={styles.label}>
          Username
          <input
            className={styles.input}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            minLength={3}
            autoComplete="username"
            required
          />
        </label>

        <label className={styles.label}>
          Email
          <input
            className={styles.input}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
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
            minLength={8}
            autoComplete="new-password"
            required
          />
        </label>

        <label className={styles.label}>
          Confirm Password
          <input
            className={styles.input}
            type="password"
            placeholder="Re-enter your password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </label>

        {/* Client-side validation message: red, small, below Confirm Password.
            Styled inline so the shared Auth.module.css (also used by Login)
            stays untouched. */}
        {validationError && (
          <p
            style={{
              color: "#E50914",
              fontSize: "0.8rem",
              margin: "-0.5rem 0 1rem",
            }}
          >
            {validationError}
          </p>
        )}

        <button className={styles.submit} type="submit" disabled={loading}>
          {loading ? "Signing up..." : "Sign Up"}
        </button>

        <p className={styles.switch}>
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
