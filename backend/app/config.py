"""Runtime settings, all overridable through environment variables or the repo-root .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", ".env"), extra="ignore")

    gemini_api_key: str = ""
    agent_model: str = "gemini-3.8-flash"
    cheap_model: str = "gemini-3.5-flash-lite"
    transcribe_model: str = "gemini-3.5-transcribe"
    tts_model: str = "gemini-3.8-flash-tts"

    # data.gov.in publishes this sample key for open APIs; it caps responses at 10 records.
    data_gov_api_key: str = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"

    contact_email: str = "fasal-kavach@users.noreply.github.com"
    cache_path: Path = ROOT / "data" / "cache" / "cache.sqlite"
    frontend_dist: Path = ROOT / "frontend" / "dist"

    http_timeout_s: float = 8.0
    cog_timeout_s: float = 20.0
    llm_timeout_s: float = 60.0
    request_budget_s: float = 90.0
    max_tool_calls: int = 10
    max_repairs: int = 2
    max_output_tokens: int = 2048

    @property
    def user_agent(self) -> str:
        return f"FasalKavach/0.1 (+https://github.com/shubhambhattog/fasal-kavach; {self.contact_email})"


settings = Settings()
