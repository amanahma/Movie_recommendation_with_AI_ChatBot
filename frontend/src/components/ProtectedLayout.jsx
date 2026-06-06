import { Navigate, Outlet } from "react-router-dom";
import { isLoggedIn } from "../services/api";
import Navbar from "./Navbar";
import styles from "./ProtectedLayout.module.css";

// Wraps all authenticated pages. If there's no JWT, bounce to /login.
// Otherwise render the navbar plus the matched child route via <Outlet>.
export default function ProtectedLayout() {
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace />;
  }
  return (
    <>
      <Navbar />
      <main className={styles.main}>
        <Outlet />
      </main>
    </>
  );
}
