from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    All optional fields have sensible defaults for development.
    """
    
    # ============================================
    # REQUIRED — Database
    # ============================================
    DATABASE_URL: str
    
    # ============================================
    # JWT / Authentication
    # ============================================
    JWT_SECRET: Optional[str] = "dev-secret-change-in-production-min-32-chars-long"
    JWT_REFRESH_SECRET: Optional[str] = "dev-refresh-secret-change-in-production-min-32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ============================================
    # APP
    # ============================================
    APP_NAME: str = "NexroCampus"
    FRONTEND_URL: str = "http://localhost:5173"
    DEBUG: bool = True
    
    # ============================================
    # GOOGLE OAUTH
    # ============================================
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # ============================================
    # GITHUB OAUTH
    # ============================================
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    
    # ============================================
    # EMAIL (SMTP)
    # ============================================
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    
    # ============================================
    # AI SERVICES
    # ============================================
    HF_TOKEN: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # ============================================
    # VECTOR DATABASE (Qdrant)
    # ============================================
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    
    # ============================================
    # FILE UPLOAD
    # ============================================
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 52428800  # 50MB
    
    # ============================================
    # CORS
    # ============================================
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # ============================================
    # PYDANTIC CONFIG
    # ============================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # ✅ Ignore extra env variables
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance (singleton pattern)"""
    return Settings()


# Global settings instance
settings = get_settings()