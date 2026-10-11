"""Central configuration. Everything is env-overridable so Docker can inject it."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "JobQuest"
    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week
    algorithm: str = "HS256"

    database_url: str = "sqlite:///./jobquest.db"

    # AI provider: auto (Ollama, then Gemini, then built-in fallback),
    # ollama, gemini, or local.
    ai_provider: str = "auto"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    # Keep API keys in environment variables; never hard-code them here.
    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Auto-apply behaviour. "demo" simulates submission (safe, testable).
    # "live" uses Playwright against real forms (requires user config + a real browser).
    apply_mode: str = "demo"

    # Job scraping. "seed" uses the built-in sample job feed (testable offline).
    # "live" uses the Playwright scraper.
    job_source: str = "seed"

    # ---- Daily automation (the scheduler) ----
    # When enabled, JobQuest runs auto-apply once a day for every user who has
    # turned autopilot on, at the configured local time.
    schedule_enabled: bool = True
    schedule_hour: int = 8          # 24h clock
    schedule_minute: int = 0
    schedule_timezone: str = "UTC"  # e.g. "America/New_York", "Asia/Dhaka"


settings = Settings()
