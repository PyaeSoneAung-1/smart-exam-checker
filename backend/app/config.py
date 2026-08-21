from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Exam Answer Checker"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "sqlite:///./smart_exam.db"

    # Redis (optional — requires running Redis server)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # SMTP Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_TLS: bool = True
    
    # Sentry
    SENTRY_DSN: Optional[str] = None
    
    # File uploads
    UPLOAD_DIR: str = "./uploads"
    
    # WebSocket
    WS_ENABLED: bool = True

    # JWT
    JWT_SECRET: str = "super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # NLP
    SPACY_MODEL: str = "en_core_web_sm"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    LANGUAGE_TOOL_URL: Optional[str] = None
    LANGUAGE_TOOL_LANGUAGE: str = "en-US"

    # AI detection (real language-model based; falls back to heuristics
    # automatically when the model is not installed)
    AI_LM_ENABLED: bool = True
    AI_MODEL: str = "distilgpt2"
    AI_MAX_TOKENS: int = 512

    # Plagiarism detection: semantic (embedding) similarity layer; falls back
    # to lexical-only automatically when the model is not installed
    PLAGIARISM_EMBEDDINGS_ENABLED: bool = True

    # Scoring weights
    KEYWORD_WEIGHT: float = 0.30
    SIMILARITY_WEIGHT: float = 0.40
    GRAMMAR_WEIGHT: float = 0.15
    COMPLETENESS_WEIGHT: float = 0.15

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Admin seed
    ADMIN_EMAIL: str = "admin@smartexam.com"
    ADMIN_PASSWORD: str = "admin123456"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
