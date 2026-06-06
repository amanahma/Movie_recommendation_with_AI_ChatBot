"""
Central application configuration.

We use pydantic-settings to read values from environment variables (and the
`.env` file in development). Defining settings in one typed place means the
rest of the app never touches `os.environ` directly -- it just imports
`settings` and gets validated, autocompleted values.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All environment-driven configuration for the backend.

    Each attribute maps to an environment variable of the same name
    (case-insensitive). Missing required values raise an error at startup,
    which is exactly what you want -- fail loudly instead of silently
    running with a broken config.
    """

    # Required: PostgreSQL connection string.
    DATABASE_URL: str

    # Required: secret used for signing tokens (auth comes in a later phase).
    SECRET_KEY: str

    # --- LLM (Groq) ---
    # Groq's API is OpenAI-compatible, so the later LLM phase will use the
    # OpenAI SDK with these values. All optional until that phase lands.
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # --- TMDB (used by scripts/import_movies.py to fetch a real catalog) ---
    TMDB_API_KEY: str = ""

    # Tell pydantic-settings to load from a local .env file if present.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unrelated env vars instead of erroring
    )


# A single shared instance imported across the app.
settings = Settings()
