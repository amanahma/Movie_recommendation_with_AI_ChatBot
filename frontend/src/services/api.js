// Centralized API layer: every fetch() to the backend goes through here.
// Also owns JWT storage (localStorage) and a tiny decoder to read the
// logged-in user's id out of the token.
//
// Backend runs on :8000; this frontend runs on Vite's :5173.

const API_BASE = "http://localhost:8000";
const TOKEN_KEY = "jwt_token";

// --- Token storage -------------------------------------------------------
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isLoggedIn() {
  return Boolean(getToken());
}

// Decode the user id from the JWT's `sub` claim without any library.
// JWTs are three base64url segments; the middle one is the JSON payload.
export function getUserId() {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(payload)
        .split("")
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join("")
    );
    return JSON.parse(json).sub;
  } catch {
    return null; // malformed token
  }
}

// --- Core request helper -------------------------------------------------
// Adds the base URL, JSON headers, and (for protected routes) the Bearer
// token. Normalizes errors into a thrown Error with a friendly message so
// every caller can just try/catch and show err.message.
async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    // fetch only rejects on network-level failures (server down, CORS, etc.)
    throw new Error("Can't reach the server. Is the backend running on :8000?");
  }

  // Expired/invalid token: clear it so the app falls back to the login page.
  if (res.status === 401 && auth) {
    clearToken();
    throw new Error("Your session expired. Please log in again.");
  }

  // Parse the body (may be empty for some responses).
  const raw = await res.text();
  let data = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = raw;
    }
  }

  if (!res.ok) {
    // FastAPI puts errors in `detail` (string or validation array).
    let message = `Request failed (${res.status})`;
    if (data && data.detail) {
      message =
        typeof data.detail === "string"
          ? data.detail
          : "Please check your input and try again.";
    }
    throw new Error(message);
  }

  return data;
}

// --- Auth ----------------------------------------------------------------
export function register({ username, email, password }) {
  return request("/auth/register", {
    method: "POST",
    body: { username, email, password },
    auth: false,
  });
}

export async function login({ username, password }) {
  const data = await request("/auth/login", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
  setToken(data.access_token); // persist JWT for subsequent calls
  return data;
}

export function logout() {
  clearToken();
}

// --- Content (unified movies + series) -----------------------------------
// List content, optionally filtered. `type` is 'movie' | 'series' | null.
export async function getContent({
  type = null,
  genre = null,
  search = null,
  limit = 1000, // headroom: 222 movies + 243 series = 465; backend caps at 1000
} = {}) {
  const params = new URLSearchParams();
  if (type) params.set("content_type", type);
  if (genre) params.set("genre", genre);
  if (search) params.set("search", search);
  params.set("limit", String(limit));
  const page = await request(`/content?${params.toString()}`);
  return page.items; // unwrap the paginated envelope
}

// Fetch a single content item by id.
export function getContentById(id) {
  return request(`/content/${id}`);
}

// --- Back-compat aliases (old movie-named functions) ---------------------
export const getMovies = getContent;        // getMovies({limit}) -> list
export const getMovie = getContentById;     // getMovie(id) -> one item
export function searchByGenre(genre) {
  return getContent({ genre });
}

// --- Interactions --------------------------------------------------------
export function markWatched(contentId, rating = null) {
  return request("/interactions", {
    method: "POST",
    body: { content_id: contentId, watched: true, rating },
  });
}

// --- Recommendations -----------------------------------------------------
export function getRecommendations(userId, useLlm = true) {
  return request(`/recommendations/${userId}?use_llm=${useLlm}`);
}

// --- Chat ----------------------------------------------------------------
export function sendChat(message) {
  return request("/chat", { method: "POST", body: { message } });
}
