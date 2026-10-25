from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    clerk_jwks_url: str
    clerk_secret_key: str | None = None
    # Optional: when set, the JWT `iss` claim must match (e.g. https://<domain>.clerk.accounts.dev)
    clerk_issuer: str | None = None
    cors_origins: str = "http://localhost:3000"
    gemini_api_key: str | None = None
    gemini_model_router: str = "gemma-3-27b-it"
    gemini_model_vision: str = "gemma-3-27b-it"
    gemini_model_filter: str = "gemini-2.5-flash-lite"  # cheap, fast — context pruning
    gemini_model_tutor: str = "gemini-3.1-flash-lite"
    gemini_model_draw: str = "gemini-3.1-flash-lite"

    # Max AI requests per user per rolling minute (chat, stream, vision-sync, draw)
    ai_rate_limit_per_minute: int = 20
    # Number of newest snapshot versions kept per board
    snapshot_retention: int = 50
    # Attempts for transient (HTTP 503) Gemini errors, exponential backoff
    gemini_max_attempts: int = 3

    def sync_database_url(self) -> str:
        """Sync driver URL for Alembic (psycopg)."""
        url = self.database_url
        if "+asyncpg" in url:
            return url.replace("+asyncpg", "+psycopg", 1)
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url


settings = Settings()
