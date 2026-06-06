import { useEffect, useState } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import { getMovie, markWatched } from "../services/api";
import Spinner from "../components/Spinner";
import ErrorMessage from "../components/ErrorMessage";
import styles from "./MovieDetailPage.module.css";

// Content detail: full info, the LLM-generated summary (the description
// field), and a "Mark as Watched" action.
//
// The back link returns to the SAME filtered browse view the user came from.
// ContentCard passes the originating query string ("?tab=series&genre=...")
// via nav state; we read it here to build the back URL and its label. If the
// page was opened directly (no state), we fall back to plain /home.
export default function MovieDetailPage() {
  const { id } = useParams();
  const location = useLocation();

  const from = location.state?.from || "";        // e.g. "?tab=series&genre=Comedy"
  const backUrl = `/home${from}`;
  const fromTab = new URLSearchParams(from).get("tab");
  const backLabel =
    fromTab === "series"
      ? "← Back to series"
      : fromTab === "movies"
        ? "← Back to movies"
        : "← Back to browse";

  const [movie, setMovie] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // "Mark as Watched" has its own independent status so it doesn't disturb
  // the page load state.
  const [watchState, setWatchState] = useState("idle"); // idle|saving|done|error
  const [watchError, setWatchError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setMovie(await getMovie(id));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  async function handleWatched() {
    setWatchState("saving");
    setWatchError("");
    try {
      await markWatched(Number(id));
      setWatchState("done");
    } catch (err) {
      setWatchState("error");
      setWatchError(err.message);
    }
  }

  if (loading) return <Spinner label="Loading..." />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;
  if (!movie) return null;

  return (
    <article className={styles.wrap}>
      <Link to={backUrl} className={styles.back}>
        {backLabel}
      </Link>

      <div className={styles.header}>
        <h1 className={styles.title}>{movie.title}</h1>
        <p className={styles.meta}>
          {movie.genre}
          {movie.year ? ` · ${movie.year}` : ""}
          {movie.rating != null ? ` · ⭐ ${movie.rating}` : ""}
        </p>
      </div>

      {/* LLM-generated summary (the description column). */}
      <section className={styles.summary}>
        <h2 className={styles.summaryHeading}>Summary</h2>
        <p className={styles.summaryText}>
          {movie.description || "No summary available for this title yet."}
        </p>
      </section>

      <div className={styles.actions}>
        <button
          className={styles.watchBtn}
          onClick={handleWatched}
          disabled={watchState === "saving" || watchState === "done"}
        >
          {watchState === "saving" && "Saving..."}
          {watchState === "done" && "✓ Added to your watched list"}
          {(watchState === "idle" || watchState === "error") &&
            "Mark as Watched"}
        </button>
        <ErrorMessage message={watchError} />
      </div>
    </article>
  );
}
