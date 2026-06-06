// TMDB poster lookup. Fails soft: any problem (missing key, network error,
// no match, bad JSON) resolves to null so the caller falls back to the
// colored letter card. The API key comes from Vite's env.

const API_KEY = import.meta.env.VITE_TMDB_API_KEY;
const TMDB_BASE = "https://api.themoviedb.org/3";
const IMAGE_BASE = "https://image.tmdb.org/t/p/w300";

// Look up a poster for a title/year. `type` selects the TMDB search endpoint
// ('series' -> /search/tv, anything else -> /search/movie) since TV titles
// live in a different search index; the image API is identical for both.
// Returns the full w300 poster URL, or null on no result / failure / no key.
export async function fetchPosterUrl(title, year, type = "movie") {
  if (!API_KEY) return null; // no key -> graceful fallback, no request

  try {
    const isSeries = type === "series";
    const endpoint = isSeries ? "/search/tv" : "/search/movie";
    const params = new URLSearchParams({ api_key: API_KEY, query: title });
    if (year) {
      params.set(isSeries ? "first_air_date_year" : "year", String(year));
    }

    const res = await fetch(`${TMDB_BASE}${endpoint}?${params.toString()}`);
    if (!res.ok) return null;

    const data = await res.json();
    const firstHit = data.results && data.results[0];
    if (!firstHit || !firstHit.poster_path) return null;

    return `${IMAGE_BASE}${firstHit.poster_path}`;
  } catch {
    return null; // network / parse failure -> fall back silently
  }
}
