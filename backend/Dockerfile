FROM python:3.11-slim

# ── System dependencies ────────────────────────────────────────────
# * libpq-dev / build-essential: psycopg2 and other native builds
# * openjdk-17-jre-headless: LanguageTool (grammar checking) runs on the JVM
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    openjdk-17-jre-headless \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ── Python dependencies (cached layer) ─────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Optional AI extras (LM-based AI detection + semantic embeddings).
# Build with:  docker build --build-arg INSTALL_AI_DEPS=true .
ARG INSTALL_AI_DEPS=false
COPY requirements-ai.txt .
RUN if [ "$INSTALL_AI_DEPS" = "true" ]; then \
        pip install torch --index-url https://download.pytorch.org/whl/cpu && \
        pip install -r requirements-ai.txt ; \
    fi

# Pre-download the spaCy model used by the scorer
RUN python -m spacy download en_core_web_sm

# Pre-cache the embedding model (~90 MB) so the first request is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Application ────────────────────────────────────────────────────
COPY . .

# Run as an unprivileged user (uploaded files and the SQLite DB live in /app)
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app
USER appuser

ENV ENVIRONMENT=production
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Apply migrations when a real database is configured, then serve.
# (SQLite dev databases are created automatically on startup.)
CMD ["sh", "-c", "alembic upgrade head 2>/dev/null || true; exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
