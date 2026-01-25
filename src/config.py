"""
ASTRAEUS - Autonomous Life Orchestrator
Configuration Management Module

This module handles all configuration loading from environment variables
with validation using Pydantic Settings.
"""

from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings can be overridden via .env file or environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # -----------------------------
    # Telegram Configuration
    # -----------------------------
    telegram_bot_token: str = Field(
        ...,
        description="Telegram Bot API token from @BotFather"
    )
    telegram_authorized_user_id: int = Field(
        ...,
        description="Telegram user ID authorized to use the bot"
    )
    
    # -----------------------------
    # AI/LLM Configuration
    # -----------------------------
    ai_provider: Literal["openai", "gemini", "ollama"] = Field(
        default="gemini",
        description="AI provider to use"
    )
    
    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model")
    
    # Gemini
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-pro", description="Gemini model")
    
    # Ollama
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama host URL")
    ollama_model: str = Field(default="llama3", description="Ollama model name")
    
    # -----------------------------
    # Location & Maps Configuration
    # -----------------------------
    google_maps_api_key: str = Field(default="", description="Google Maps API key")
    use_openstreetmap: bool = Field(default=True, description="Use OpenStreetMap instead of Google Maps")
    default_city: str = Field(default="Istanbul", description="Default city")
    default_country: str = Field(default="TR", description="Default country code")
    default_timezone: str = Field(default="Europe/Istanbul", description="Default timezone")
    
    # -----------------------------
    # Weather Configuration
    # -----------------------------
    openweathermap_api_key: str = Field(default="", description="OpenWeatherMap API key")
    rain_time_buffer: int = Field(default=20, description="Extra time for rain (percentage)")
    snow_time_buffer: int = Field(default=30, description="Extra time for snow (percentage)")
    heavy_traffic_buffer: int = Field(default=25, description="Extra time for heavy traffic (percentage)")
    
    # -----------------------------
    # Database Configuration
    # -----------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://astraeus:astraeus_password@localhost:5432/astraeus_db",
        description="PostgreSQL connection URL"
    )
    
    # -----------------------------
    # User Configuration
    # -----------------------------
    user_name: str = Field(default="Tarık", description="User's name for personalized messages")
    default_prep_time: int = Field(default=5, description="Default preparation time in minutes")
    event_check_interval: int = Field(default=60, description="Event check interval in seconds")
    min_warning_time: int = Field(default=15, description="Minimum warning time before events in minutes")
    
    # -----------------------------
    # Application Settings
    # -----------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )
    environment: Literal["development", "production"] = Field(
        default="development",
        description="Application environment"
    )
    
    # Webhook settings for production
    webhook_url: str = Field(default="", description="Webhook URL for production")
    webhook_port: int = Field(default=8443, description="Webhook port")


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()


# Convenience alias
settings = get_settings()
