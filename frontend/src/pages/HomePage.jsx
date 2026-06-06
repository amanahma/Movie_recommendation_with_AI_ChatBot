import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getContent } from "../services/api";
import ContentCard from "../components/ContentCard";
import Spinner from "../components/Spinner";
import ErrorMessage from "../components/ErrorMessage";
import styles from "./HomePage.module.css";

// Home: the unified catalog (movies + series) as a poster grid, with type
// tabs (All / Movies / Series), a genre dropdown, and a title search.
//
// Tab + genre live in the URL query string (?tab=series&genre=Comedy) via
// useSearchParams, so the browser back/forward buttons restore the filtered
// view natively. The search box stays ephemeral local state by design.
//
// Note: the URL tab value is 'movies' (plural) but the data's content_type
// is 'movie' (singular), so each tab carries the `type` it maps to.
const TABS = [
  { key: "all", label: "All", type: null },
  { key: "movies", label: "Movies", type: "movie" },
  { key: "series", label: "Series", type: "series" },
];

export default function HomePage() {
  const [all, setAll] = useState([]); // full catalog
  const [query, setQuery] = useState(""); // search — ephemeral, not in URL
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // --- URL-backed state ---
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get("tab") || "all";
  // Guard against bogus ?tab= values falling back to "all".
  const activeTab = TABS.some((t) => t.key === rawTab) ? rawTab : "all";
  const activeGenre = searchParams.get("genre") || ""; // "" = All genres

  // Update one query param while preserving the others. Empty value (or the
  // "all" tab) removes the param so the URL stays clean.
  function setParam(key, value) {
    const next = new URLSearchParams(searchParams);
    if (!value || (key === "tab" && value === "all")) {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    setSearchParams(next);
  }

  async function load() {
    setLoading(true);
    setError("");
    try {
      setAll(await getContent({ limit: 1000 })); // everything, one call
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  // Genres for the dropdown, derived from the full catalog.
  const genres = useMemo(
    () => [...new Set(all.map((c) => c.genre).filter(Boolean))].sort(),
    [all]
  );

  // Apply tab + genre + title filters (all client-side).
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const type = (TABS.find((t) => t.key === activeTab) || {}).type;
    return all.filter((c) => {
      if (type && c.content_type !== type) return false;
      if (activeGenre && c.genre !== activeGenre) return false;
      if (q && !c.title.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [all, activeTab, activeGenre, query]);

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>Browse Movies &amp; Series</h1>

      <div className={styles.controls}>
        <input
          className={styles.search}
          placeholder="Search movies and series..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className={styles.select}
          value={activeGenre || "All"}
          onChange={(e) =>
            setParam("genre", e.target.value === "All" ? "" : e.target.value)
          }
        >
          <option value="All">All genres</option>
          {genres.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
      </div>

      {/* Type tabs with a Netflix-red underline on the active one. */}
      <div className={styles.tabs}>
        {TABS.map((t) => (
          <button
            key={t.key}
            className={
              activeTab === t.key ? `${styles.tab} ${styles.tabActive}` : styles.tab
            }
            onClick={() => setParam("tab", t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <Spinner label="Loading catalog..." />}
      <ErrorMessage message={error} onRetry={load} />

      {!loading && !error && visible.length === 0 && (
        <p className={styles.empty}>Nothing matches your filters.</p>
      )}

      {!loading && !error && visible.length > 0 && (
        <div className={styles.grid}>
          {visible.map((item) => (
            <ContentCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
