import { useState } from "react";
import styles from "./WhyThis.module.css";

// The per-card recommendation explainer. The LLM reason shows underneath
// the card always; the "Why this?" toggle expands to reveal the match
// score detail. Used in the recommendations grid.
export default function WhyThis({ reason, score }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={styles.wrap}>
      <p className={styles.reason}>{reason}</p>

      <button
        className={styles.toggle}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        {open ? "Hide" : "Why this?"}
      </button>

      {open && (
        <div className={styles.detail}>
          This pick scored <strong>{score.toFixed(2)}</strong> based on how
          strongly viewers with similar taste to you watched it.
        </div>
      )}
    </div>
  );
}
