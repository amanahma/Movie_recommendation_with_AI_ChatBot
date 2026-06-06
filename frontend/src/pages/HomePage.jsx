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
// The active tab lives in the URL (?tab=series) so back/forward restore it.
// The genre is PER-TAB and remembered independently per tab.
//
// Note: URL tab value is 'movies' (plural) but the data's content_type is
// 'movie' (singular), so each tab carries the `type` it maps to.
const TABS = [
  { key: "all", label: "All", type: null },
  { key: "movies", label: "Movies", type: "movie" },
  { key: "series", label: "Series", type: "series" },
];

// Per-tab genre memory at MODULE scope (NOT inside the component, and not a
// ref). A ref is destroyed when Home unmounts on navigation to a detail page,
// so the genre was lost on "← back". A module-level variable persists for the
// whole browser session regardless of mount/unmount, so each tab's genre
// survives navigating away and back. It still resets on a full page refresh,
// which is acceptable.
const tabGenreMemory = {
  all: "",
  movies: "",
  series: "",
};

export default function HomePage() {
  const [all, setAll] = useState([]); // full catalog
  const [query, setQuery] = useState(""); // search — ephemeral, unchanged
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // --- active tab (URL-backed) ---
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get("tab") || "all";
  const activeTab = TABS.some((t) => t.key === rawTab) ? rawTab : "all";

  // The genre shown for the CURRENT tab (drives the dropdown + filtering).
  // Initialized from the module-level memory, so a remount (navigating back)
  // restores this tab's last genre. "" means "All genres".
  const [genre, setGenre] = useState(() => tabGenreMemory[activeTab] || "");

  // Restore this tab's remembered genre whenever the active tab changes —
  // covers both browser back/forward between ?tab= entries AND the component
  // remounting after returning from a detail page.
  useEffect(() => {
    setGenre(tabGenreMemory[activeTab] || "");
  }, [activeTab]);

  // Switch tabs: load the new tab's remembered genre synchronously (batched
  // with the URL change, so there's no flash of the old genre), then update
  // the URL. The previous tab's genre was already saved on every change.
  function selectTab(key) {
    setGenre(tabGenreMemory[key] || "");
    const next = new URLSearchParams(searchParams);
    if (key === "all") next.delete("tab");
    else next.set("tab", key);
    setSearchParams(next);
  }

  // Change genre for the current tab: update the displayed state AND remember
  // it against the active tab (in module memory) so it survives tab switches
  // and navigation away/back.
  function handleGenreChange(value) {
    const g = value === "All" ? "" : value;
    setGenre(g);
    tabGenreMemory[activeTab] = g;
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

  // Apply tab + (tab-specific) genre + title filters, all client-side.
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const type = (TABS.find((t) => t.key === activeTab) || {}).type;
    return all.filter((c) => {
      if (type && c.content_type !== type) return false;
      if (genre && c.genre !== genre) return false;
      if (q && !c.title.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [all, activeTab, genre, query]);

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
          value={genre || "All"}
          onChange={(e) => handleGenreChange(e.target.value)}
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
            onClick={() => selectTab(t.key)}
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
