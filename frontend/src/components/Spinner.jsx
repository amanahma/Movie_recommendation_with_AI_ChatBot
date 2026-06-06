import styles from "./Spinner.module.css";

// Reusable loading indicator with an optional label. Used for the loading
// state required on every API call.
export default function Spinner({ label = "Loading..." }) {
  return (
    <div className={styles.wrap} role="status" aria-live="polite">
      <div className={styles.spinner} />
      <span className={styles.label}>{label}</span>
    </div>
  );
}
