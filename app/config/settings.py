"""
Application Configuration Subsystem for CARA.
Loads environment variables using pydantic-settings with explicit type validation.
"""

from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Central settings model for Cost-Aware Autonomous Research & Report Agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application Core Config
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SECRET_KEY: str = "change-this-in-production-use-a-strong-random-secret"

    # LLM Provider API Keys
    GROQ_API_KEY: str = Field(default="", description="API key for Groq Cloud")
    GEMINI_API_KEY: str = Field(default="", description="API key for Google Gemini")
    OPENROUTER_API_KEY: str = Field(default="", description="API key for OpenRouter")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Base URL for Ollama local service")

    # Hard Budget & Loop Limits (Cost-Aware Guardrails)
    MAX_RESEARCH_ITERATIONS: int = Field(default=3, description="Maximum research loop iterations")
    MAX_MODEL_CALLS: int = Field(default=10, description="Maximum LLM API calls allowed per task")
    MAX_TOOL_CALLS: int = Field(default=20, description="Maximum tool calls allowed per task")
    MAX_TOKENS: int = Field(default=15000, description="Maximum total tokens allowed per task")
    MAX_EXECUTION_TIME: int = Field(default=120, description="Maximum task execution timeout in seconds")
    MAX_PROVIDER_RETRIES: int = Field(default=2, description="Maximum retries per provider before fallback")

    # Tool & Security Boundaries
    ALLOWED_DOCUMENT_DIR: Path = Field(
        default=Path("data/documents"), description="Allowed directory for local document search"
    )
    URL_READER_TIMEOUT: int = Field(default=15, description="Timeout in seconds for URL fetching")
    URL_READER_MAX_BYTES: int = Field(default=1048576, description="Max allowed response size (1 MB)")

    # Rate Limiting & Session Management
    RATE_LIMIT_MAX_REQUESTS: int = Field(
        default=10, description="Max requests per session within the sliding window"
    )
    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60, description="Sliding window duration in seconds for rate limiting"
    )
    SESSION_TOKEN_TTL_HOURS: int = Field(
        default=24, description="Session token validity in hours before expiry"
    )

    # Storage & Caching
    DATABASE_URL: str = Field(default="sqlite:///./data/cara.db", description="Database connection URL")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL for caching")

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


# Singleton instance
settings = AppSettings()
