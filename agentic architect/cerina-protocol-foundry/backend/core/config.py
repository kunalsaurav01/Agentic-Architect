"""
Cerina Protocol Foundry - Configuration Management
"""

import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Cerina Protocol Foundry"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")
    environment: Literal["development", "staging", "production"] = "development"

    # API Server
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = Field(
        default="sqlite:///./cerina_foundry.db",
        alias="DATABASE_URL"
    )
    sql_debug: bool = Field(default=False, alias="SQL_DEBUG")

    # LLM Configuration
    llm_provider: Literal["gemini"] = Field(
        default="gemini",
        alias="LLM_PROVIDER"
    )
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")

    # Gemini specific
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")
    gemini_temperature: float = Field(default=0.7, alias="GEMINI_TEMPERATURE")

    # Agent Configuration
    max_iterations: int = Field(default=5, alias="MAX_ITERATIONS")
    agent_timeout: int = Field(default=120, alias="AGENT_TIMEOUT")  # seconds

    # Safety Thresholds
    min_safety_score: float = Field(default=7.0, alias="MIN_SAFETY_SCORE")
    min_clinical_score: float = Field(default=6.0, alias="MIN_CLINICAL_SCORE")
    min_empathy_score: float = Field(default=6.0, alias="MIN_EMPATHY_SCORE")

    # Human-in-the-Loop
    require_human_approval: bool = Field(default=True, alias="REQUIRE_HUMAN_APPROVAL")
    approval_timeout: int = Field(default=3600, alias="APPROVAL_TIMEOUT")  # seconds

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS"
    )

    # WebSocket
    ws_heartbeat_interval: int = Field(default=30, alias="WS_HEARTBEAT_INTERVAL")

    # MCP Server
    mcp_enabled: bool = Field(default=True, alias="MCP_ENABLED")
    mcp_host: str = Field(default="0.0.0.0", alias="MCP_HOST")
    mcp_port: int = Field(default=8001, alias="MCP_PORT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        alias="LOG_FORMAT"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_llm_api_key(self) -> str:
        """Get the API key for the configured LLM provider."""
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required when using Gemini provider")
        return self.google_api_key

    def get_llm_model(self) -> str:
        """Get the model name for the configured LLM provider."""
        return self.gemini_model

    def get_llm_temperature(self) -> float:
        """Get the temperature for the configured LLM provider."""
        return self.gemini_temperature


# Global settings instance
settings = Settings()


# Logging configuration
import logging


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


setup_logging()
