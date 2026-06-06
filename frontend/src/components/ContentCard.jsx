import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { fetchPosterUrl } from "../utils/tmdb";
import styles from "./ContentCard.module.css";

// Module-level poster cache shared by every card across all pages.
const posterCache = {};

// Deterministic gradient for the fallback poster (no real image available).
function posterGradient(title) {
  let hash = 0;
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `linear-gradient(150deg, hsl(${hue} 55% 32%), hsl(${(hue + 40) % 360} 55% 22%))`;
}

// "3 Seasons · 30 Episodes", or "? Seasons" when season data is missing.
function seasonsLabel(item) {
  const s =
    item.seasons != null
      ? `${item.seasons} Season${item.seasons === 1 ? "" : "s"}`
      : "? Seasons";
  const e =
    item.episodes != null
      ? ` · ${item.episodes} Episode${item.episodes === 1 ? "" : "s"}`
      : "";
  return s + e;
}

// Netflix-style content card for a movie OR series. Poster-only at rest with
// a type badge top-left; on hover it scales and reveals title/genre/rating
// (plus seasons/episodes for series) and a Watch button. Optional `footer`
// slot renders below the poster (recommendations reason / mood badge).
export default function ContentCard({ item, footer }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isSeries = item.content_type === "series";
  const [poster, setPoster] = useState(() => posterCache[item.id] ?? null);

  useEffect(() => {
    let cancelled = false;
    if (item.id in posterCache) {
      setPoster(posterCache[item.id]);
      return;
    }
    fetchPosterUrl(item.title, item.year, item.content_type).then((url) => {
      posterCache[item.id] = url;
      if (!cancelled) setPoster(url);
    });
    return () => {
      cancelled = true;
    };
  }, [item.id, item.title, item.year, item.content_type]);

  function handleImgError() {
    posterCache[item.id] = null;
    setPoster(null);
  }

  // Pass the current page's query string (e.g. "?tab=series&genre=Comedy")
  // as nav state so the detail page's back link can return to this exact
  // filtered view.
  const goToDetail = () =>
    navigate(`/movie/${item.id}`, { state: { from: location.search } });

  return (
    <article className={styles.card}>
      <div
        className={styles.posterWrap}
        onClick={goToDetail}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && goToDetail()}
      >
        {/* Type badge: SERIES (red) / FILM (dark gray), visible at rest. */}
        <span className={isSeries ? styles.badgeSeries : styles.badgeFilm}>
          {isSeries ? "SERIES" : "FILM"}
        </span>

        {poster ? (
          <img
            className={styles.img}
            src={poster}
            alt={`${item.title} poster`}
            loading="lazy"
            onError={handleImgError}
          />
        ) : (
          <div
            className={styles.fallback}
            style={{ background: posterGradient(item.title) }}
          >
            <span className={styles.posterLetter}>{item.title[0]}</span>
          </div>
        )}

        <div className={styles.overlay}>
          <h3 className={styles.title}>{item.title}</h3>
          <p className={styles.meta}>
            {item.genre}
            {item.year ? ` · ${item.year}` : ""}
            {item.rating != null ? ` · ⭐ ${item.rating}` : ""}
          </p>
          {/* Series get a seasons/episodes line below the rating. */}
          {isSeries && <p className={styles.series}>{seasonsLabel(item)}</p>}
          <button
            className={styles.watch}
            onClick={(e) => {
              e.stopPropagation();
              goToDetail();
            }}
          >
            ▶ Watch
          </button>
        </div>
      </div>

      {footer && <div className={styles.footer}>{footer}</div>}
    </article>
  );
}
