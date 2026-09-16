"""Application configuration.

Values come from (in order of precedence): environment variables, a local
`.env` file, then the defaults declared here. A few defaults are resolved at
startup time by :meth:`Settings.model_post_init` so that the app is safe by
default in production while staying zero-config for local development.
"""
import os
import secrets
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
_UPLOADS_DIR = BACKEND_DIR / "uploads"
_JWT_SECRET_FILE = BACKEND_DIR / ".jwt_secret"

DEV_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3090",
    "http://127.0.0.1:3090",
]


def _persisted_dev_secret() -> str:
    """Return a JWT secret for local development.

    Never a hard-coded value that could ship to production: the first run
    generates a random secret and persists it to `backend/.jwt_secret`
    (git-ignored, mode 0600) so tokens stay valid across restarts.
    """
    env_secret = os.environ.get("JWT_SECRET")
    if env_secret:
        return env_secret
    if _JWT_SECRET_FILE.exists():
        stored = _JWT_SECRET_FILE.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    generated = secrets.token_urlsafe(48)
    try:
        _JWT_SECRET_FILE.write_text(generated, encoding="utf-8")
        _JWT_SECRET_FILE.chmod(0o600)
    except OSError:  # read-only FS — still usable for this process
        pass
    return generated


class Settings(BaseSettings):
    # ── Core ────────────────────────────────────────────────
    PROJECT_NAME: str = "Smart Exam Answer Checker"
    PROJECT_VERSION: str = "1.1.0"
    API_V1_PREFIX: str = "/api"

    # "development" | "production" | "test"
    ENVIRONMENT: str = "development"

    # ── Database ───────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./smart_exam.db"

    # ── Email / monitoring (optional) ──────────────────────
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_TLS: bool = True
    SENTRY_DSN: Optional[str] = None

    # ── File uploads ───────────────────────────────────────
    UPLOAD_DIR: str = str(_UPLOADS_DIR)
    # Uploaded files are private by default and served through the
    # authenticated `/api/files/{path}` endpoint. Set to true only when the
    # host already protects the uploads directory.
    UPLOADS_PUBLIC: bool = False

    # ── WebSocket ──────────────────────────────────────────
    WS_ENABLED: bool = True

    # ── JWT / auth ─────────────────────────────────────────
    # Leave unset in development (a random secret is generated and persisted);
    # REQUIRED when ENVIRONMENT=production.
    JWT_SECRET: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Rate limiting (per client IP). Set RATE_LIMIT_ENABLED=false to disable.
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "120/minute"
    RATE_LIMIT_LOGIN: str = "10/minute"

    # ── Demo data / seed accounts ──────────────────────────
    # Demo seeding is skipped in production unless explicitly enabled.
    SEED_DEMO_DATA: Optional[bool] = None
    DEMO_PASSWORD: Optional[str] = None
    ADMIN_EMAIL: str = "admin@smartexam.com"
    ADMIN_PASSWORD: Optional[str] = None
    # Bulk CSV import: when unset each imported user gets a random password
    # which is returned once in the API response.
    BULK_IMPORT_PASSWORD: Optional[str] = None

    # ── API docs ───────────────────────────────────────────
    ENABLE_DOCS: Optional[bool] = None

    # ── NLP ────────────────────────────────────────────────
    SPACY_MODEL: str = "en_core_web_sm"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    LANGUAGE_TOOL_URL: Optional[str] = None
    LANGUAGE_TOOL_LANGUAGE: str = "en-US"
    # Set to false to skip spawning the Java LanguageTool server and use the
    # built-in rule checks only (the test suite does this; also handy on hosts
    # without a JVM).
    LANGUAGE_TOOL_ENABLED: bool = True

    # AI detection (real language-model based; falls back to heuristics
    # automatically when the model is not installed)
    AI_LM_ENABLED: bool = True
    AI_MODEL: str = "distilgpt2"
    AI_MAX_TOKENS: int = 512
    AI_FLAG_THRESHOLD: float = 0.45
    AI_REVIEW_THRESHOLD: float = 0.25

    # Plagiarism detection
    PLAGIARISM_EMBEDDINGS_ENABLED: bool = True
    # Lexical (TF-IDF) similarity alone decides a flag — it is the only
    # trustworthy copy signal. Semantic similarity is reported as a separate
    # "review" signal for paraphrases (see app/nlp/advanced/plagiarism_detector.py).
    PLAGIARISM_SEMANTIC_REVIEW_GATE: float = 0.90
    PLAGIARISM_SEMANTIC_CORROBORATION_GATE: float = 0.92

    # ── Scoring weights ────────────────────────────────────
    KEYWORD_WEIGHT: float = 0.30
    SIMILARITY_WEIGHT: float = 0.40
    GRAMMAR_WEIGHT: float = 0.15
    COMPLETENESS_WEIGHT: float = 0.15

    # ── CORS ───────────────────────────────────────────────
    # Explicit origins only (never "*" together with credentials).
    BACKEND_CORS_ORIGINS: List[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT.lower() in ("test", "testing")

    def model_post_init(self, __context) -> None:  # noqa: D105 (pydantic hook)
        if self.JWT_SECRET and len(self.JWT_SECRET) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters (RFC 7518 recommends 32+ "
                "bytes for HS256). Generate one with: "
                "python -c \"import secrets;print(secrets.token_urlsafe(48))\""
            )
        if not self.JWT_SECRET:
            if self.is_production:
                raise RuntimeError(
                    "JWT_SECRET must be set when ENVIRONMENT=production. "
                    "Generate one with: python -c \"import secrets;print(secrets.token_urlsafe(48))\""
                )
            self.JWT_SECRET = _persisted_dev_secret()

        if self.ENABLE_DOCS is None:
            self.ENABLE_DOCS = not self.is_production

        if self.SEED_DEMO_DATA is None:
            self.SEED_DEMO_DATA = not self.is_production

        if self.DEMO_PASSWORD is None:
            self.DEMO_PASSWORD = "123456" if not self.is_production else None

        if not self.BACKEND_CORS_ORIGINS:
            self.BACKEND_CORS_ORIGINS = [] if self.is_production else list(DEV_CORS_ORIGINS)


settings = Settings()
