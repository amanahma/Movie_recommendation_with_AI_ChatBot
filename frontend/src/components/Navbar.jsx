import { NavLink, useNavigate } from "react-router-dom";
import { logout } from "../services/api";
import styles from "./Navbar.module.css";

// Top navigation shared across all protected pages. NavLink gives us the
// active-route styling for free. Logout clears the token and returns to
// the login screen.
export default function Navbar() {
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  // Helper so each link gets the "active" class when it's the current route.
  const linkClass = ({ isActive }) =>
    isActive ? `${styles.link} ${styles.active}` : styles.link;

  return (
    <header className={styles.bar}>
      <div className={styles.inner}>
        <NavLink to="/home" className={styles.brand}>
          MovieRec
        </NavLink>

        <nav className={styles.links}>
          <NavLink to="/home" className={linkClass}>
            Home
          </NavLink>
          <NavLink to="/recommendations" className={linkClass}>
            Recommendations
          </NavLink>
          <NavLink to="/chat" className={linkClass}>
            Chat with AI
          </NavLink>
          <button className={styles.logout} onClick={handleLogout}>
            Logout
          </button>
        </nav>
      </div>
    </header>
  );
}
