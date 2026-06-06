import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getRecommendations, getUserId } from "../services/api";
import ContentCard from "../components/ContentCard";
import WhyThis from "../components/WhyThis";
import Spinner from "../components/Spinner";
import ErrorMessage from "../components/ErrorMessage";
import styles from "./RecommendationsPage.module.css";

// Personalized grid for the logged-in user. The API now returns BOTH a
// detected current mood (from recent watches) and a merged list of
// collaborative + mood recommendations. We show the mood at the top and a
// "Matches your mood" badge on cards whose genre fits that mood.
export default function RecommendationsPage() {
  const [currentMood, setCurrentMood] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const userId = getUserId(); // decoded from the JWT
      if (!userId) throw new Error("Could not identify you. Please log in again.");
      const data = await getRecommendations(userId, true);
      setCurrentMood(data.current_mood);
      setItems(data.recommendations);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className={styles.page}>
      {/* Full-width Netflix-red mood banner (only when a mood was detected). */}
      {currentMood && (
        <div className={styles.moodBanner}>
          🎭 You seem to be in a <strong>{currentMood}</strong> mood
        </div>
      )}

      <div className={styles.content}>
        <h1 className={styles.heading}>Recommendations</h1>
        <p className={styles.sub}>
          A blend of viewers with similar taste and your current mood.
        </p>

        {loading && <Spinner label="Building your recommendations..." />}
        <ErrorMessage message={error} onRetry={load} />

        {/* Empty state: usually a brand-new user with no watch history. */}
        {!loading && !error && items.length === 0 && (
          <div className={styles.empty}>
            <p>No recommendations yet.</p>
            <p className={styles.emptyHint}>
              <Link to="/home" className={styles.link}>
                Browse movies
              </Link>{" "}
              and mark a few as watched — we'll learn your taste from there.
            </p>
          </div>
        )}

        {!loading && !error && items.length > 0 && (
          <div className={styles.grid}>
            {items.map(({ movie, score, reason, mood_tag }) => (
              <ContentCard
                key={movie.id}
                item={movie}
                footer={
                  <>
                    {/* Mood badge: present only on mood-matching cards.
                        Cards without it are collaborative-filtering picks. */}
                    {mood_tag && (
                      <span className={styles.moodBadge}>Matches your mood</span>
                    )}
                    <WhyThis reason={reason} score={score} />
                  </>
                }
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
