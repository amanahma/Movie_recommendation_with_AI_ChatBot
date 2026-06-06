import styles from "./ErrorMessage.module.css";

// Friendly, dismissible-looking error banner. Optionally shows a Retry
// button when an onRetry handler is provided.
export default function ErrorMessage({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className={styles.box} role="alert">
      <span className={styles.text}>⚠️ {message}</span>
      {onRetry && (
        <button className={styles.retry} onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
