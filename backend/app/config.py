"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://karya:karya@localhost:5432/karyaos"
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    llm_provider: str = "fake"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "gemini/gemini-1.5-flash"
    escalation_model: str = "gemini/gemini-1.5-pro"
    llm_confidence_threshold: float = 0.75

    # Auth
    jwt_secret: str = "dev-secret-change-me-in-prod-32ch"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    mock_api_base_url: str = "http://localhost:8001"

    # Mock failure modes
    mock_it_fail_mode: str = "none"
    mock_admin_fail_mode: str = "none"
    mock_payroll_fail_mode: str = "none"

    # Cost
    infra_cost_per_hour_inr: float = 50.0
    estimated_workflows_per_hour: int = 20

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_app_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
