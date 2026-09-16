# Smart Exam Answer Checker

Modern exam-grading platform: teachers create exams, students answer in their own
words, and an NLP engine scores the answers (keyword coverage / semantic
similarity / grammar / completeness). Admin, teacher and student dashboards each
get animated stat cards and live charts that are computed from the database, in a
dark or light theme.

Extra grading tools for teachers: **AI-generated-answer detection**
(perplexity + burstiness), **plagiarism detection** (lexical + semantic review
signal), **rubric grading**, **class intelligence reports**, per-answer feedback,
PDF/Excel export and a WebSocket channel for grade notifications.

---

## 1. What changed in this revision (v1.1.0)

Hardening and cleanup pass driven by a full security/quality review:

**Security**

- Students can no longer list other students' answers (`GET /api/answers/` is
  scoped to the caller).
- Every `/api/nlp/*` endpoint now requires a teacher/admin **and** ownership of
  the exam's subject.
- `model_answer` and `keywords` are no longer returned to students by the
  question endpoints (new `QuestionStudentResponse`).
- No hard-coded JWT secret: development gets a random secret persisted to
  `backend/.jwt_secret` (git-ignored, mode 0600); production **requires**
  `JWT_SECRET` and refuses to start without one.
- Token revocation: JWTs carry a `token_version`; logout and password change
  invalidate every previously issued token. New `POST /api/auth/logout`.
- CORS uses an explicit `BACKEND_CORS_ORIGINS` allow-list (never `*` with
  credentials) and defaults to localhost origins outside production.
- Rate limiting is actually wired up (`slowapi`): 120 req/min per IP, 10/min on
  login/refresh; GZip is enabled.
- Uploads are private: files are served through the authenticated
  `GET /api/files/{path}` (Bearer header or `?token=` for `<img>`), with
  path-traversal protection and magic-byte content validation. Static
  `/uploads` is opt-in via `UPLOADS_PUBLIC=true`.
- `/api/settings` requires authentication; `/health/system` is admin-only;
  health errors are logged, never returned; `/docs` and `/redoc` are disabled in
  production.
- Demo seeding is off in production; demo passwords come from `DEMO_PASSWORD`;
  no password is ever written to the log; CSV bulk import returns a random
  temporary password per user instead of a shared default.
- Dependencies pinned; `python-jose` (CVE-2024-33663/33664) replaced with
  `PyJWT`; `openpyxl` added to the production requirements so XLSX export works.

**Grading quality**

- Plagiarism: **only lexical (TF-IDF) similarity flags a pair**. Semantic
  (embedding) similarity is reported as a `semantic_review` signal, because
  short answers to the same question routinely exceed 0.92 cosine similarity
  even when written independently. This removes the false positives the previous
  0.92 semantic gate produced on the demo data.
- Keyword matching no longer counts a multi-word keyword as "covered" when only
  one of its words appears, and junk two-word fragments are filtered out of the
  keyword list.
- When a model answer yields no keywords the keyword weight is redistributed
  over the remaining components (instead of awarding a free 100%).
- Entity overlap is neutral (0.5) when neither text contains entities.
- Semantic similarity now uses sentence embeddings (`all-MiniLM-L6-v2`) with a
  spaCy fallback, instead of spaCy small-model tensors.
- Grammar is checked once per answer (was three times), and the LanguageTool
  URL/language and spaCy model settings are actually used.
- `CONFLICT (409)` for duplicate submissions, enforced by a real unique
  constraint on `(question_id, student_id)`.

**Engineering**

- CI workflow (`.github/workflows/ci.yml`): ruff + pytest on the backend,
  `tsc` + eslint + build on the frontend.
- Real Alembic migration (`backend/alembic/versions/0001_initial_schema.py`);
  `alembic check` reports no drift.
- `pytest.ini` with warnings-as-errors, a new `tests/test_security.py`
  (authorisation, revocation, file serving) and `tests/test_plagiarism.py`
  (flagging tiers); 112 tests, zero warnings.
- WebSocket grade notifications are actually emitted after grading (they were
  dead code).
- Dead code removed: unused response helpers, the unused cache decorator,
  unused frontend hooks/components/chart files and the broken standalone
  `public/*.html` pages.
- Frontend no longer fetches 10,000 answers to render a page; it uses targeted
  paginated queries. Type-check, lint and build are clean.

See `.github/workflows/ci.yml` for exactly what is verified on every push.

---

## 2. Prerequisites

| Tool | Version |
|---|---|
| Node.js | 20+ (18.18 is the minimum for Next 16) |
| npm | 9+ |
| Python | 3.10 – 3.12 |

No PostgreSQL required for local development — the backend defaults to
**SQLite** (`backend/smart_exam.db`).

---

## 3. Backend — run it

```bash
cd backend

# (a) virtual environment
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

# (b) dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# (c) optional: real AI-detection + semantic embeddings (~2 GB RAM)
pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-ai.txt

# (d) start the API  →  http://localhost:8000  (docs at /docs)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Everything has a safe default: with no `backend/.env` the app uses SQLite, burns
a **random** JWT secret into `backend/.jwt_secret`, enables rate limiting and
seeds the demo database.

On startup the app:

1. creates/upgrades the schema (`create_all` + `ensure_schema_upgrades`), and
2. seeds demo data when `SEED_DEMO_DATA` is on (default outside production):
   admin, 5 teachers, 5 students, 5 subjects, 5 exams, 25 questions and **125
   pre-graded answers**. Seeding is idempotent, so restarts do not duplicate it.

Seed it manually with `python -m app.seed` (after `pip install -r requirements.txt`).

### Configuration

Copy `backend/.env.example` to `backend/.env` to change anything. The settings
that matter most:

| Setting | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | `production` turns demo seeding + API docs off and requires `JWT_SECRET` |
| `DATABASE_URL` | `sqlite:///./smart_exam.db` | PostgreSQL is supported (`postgresql://user:pass@host/db`) |
| `JWT_SECRET` | generated | Required, ≥ 32 characters, in production |
| `BACKEND_CORS_ORIGINS` | localhost:3000/3090 | JSON list; empty in production until you set it |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_LOGIN` | `true` / `10/minute` | per client IP |
| `DEMO_PASSWORD` / `ADMIN_PASSWORD` | `123456` (dev) | Demo logins; production generates a random admin password and logs it once |
| `SEED_DEMO_DATA` | on in dev | Turn off for an empty database |
| `UPLOADS_PUBLIC` | `false` | Files are served via the authenticated `/api/files` route |
| `ENABLE_DOCS` | on in dev | `/docs`, `/redoc`, `/openapi.json` |
| `LANGUAGE_TOOL_ENABLED` | `true` | `false` = built-in grammar rules only (no Java); the test suite sets it to `false` |

### Migrations (production databases)

```bash
cd backend
alembic upgrade head          # create/upgrade the schema
alembic revision --autogenerate -m "describe change"
alembic check                 # verify no model/schema drift
```

### Tests

```bash
cd backend
pytest                        # 112 tests, warnings are errors
ruff check app tests          # lint
```

---

## 4. Frontend — run it

```bash
cd frontend

npm install

# point the app at the API (repo .env files are git-ignored, so create it)
printf 'NEXT_PUBLIC_API_URL=http://localhost:8000/api\n' > .env

npm run dev                   # http://localhost:3000
```

Production build:

```bash
npm run build && npm run start      # serves on :3000
npx tsc --noEmit && npm run lint    # what CI runs
```

Leave `NEXT_PUBLIC_API_URL` unset and the dev server instead proxies `/api/*` to
`http://127.0.0.1:8090` (see `next.config.ts`).

---

## 5. Demo accounts

Password for every seeded account: **`123456`** (from `DEMO_PASSWORD`).

| Role | Name | Email |
|---|---|---|
| Admin | System Admin | `admin@smartexam.com` |
| Teacher | Daw Ni Lar Win | `dawnilarwin@gmail.com` |
| Teacher | Daw Nwe Ni Win | `dawnweniwin@gmail.com` |
| Teacher | Daw Aye Thidar Win | `dawayethidarwin@gmail.com` |
| Teacher | Daw Zin Thu Thu Myint | `dawzinthuthumyint@gmail.com` |
| Teacher | Daw Tar Tar Khin | `dawtartarkhin@gmail.com` |
| Student | Pyae Sone Aung | `pyaesoneaung@gmail.com` |
| Student | Pyae Myat Phyo | `pyaemyatphyo@gmail.com` |
| Student | San Lin Aung | `sanlinaung@gmail.com` |
| Student | Swan Yee Htut | `swanyeehtut@gmail.com` |
| Student | Thura Hein | `thurahein@gmail.com` |

The demo data deliberately includes one **real plagiarism case**: Pyae Myat
Phyo's encryption answer is a verbatim copy of Pyae Sone Aung's, so the
plagiarism checker has one true positive (60% lexical threshold → flagged).

---

## 6. How grading works

```
total = (keyword·w_kw + similarity·w_sim + grammar·w_g + completeness·w_c) × question.marks
        default weights: 0.30 / 0.40 / 0.15 / 0.15  (editable in Admin → Settings)
```

| Component | What it measures |
|---|---|
| **Keyword (30%)** | Model-answer keywords (TF-IDF + spaCy entities/nouns) that appear in the student's answer. Multi-word terms count only when all of their words appear. |
| **Similarity (40%)** | Weighted mix of TF-IDF cosine (0.30), word overlap (0.20), sentence embeddings (0.25), bigram overlap (0.10), entity overlap (0.05) and concept coverage (0.10). |
| **Grammar (15%)** | LanguageTool (when installed) plus built-in rules; `1 − errors-per-100-words/10`. |
| **Completeness (15%)** | `0.7 × concept coverage of each model sentence + 0.3 × length ratio`. |

Zero-out rules: `keyword < 0.15 and similarity < 0.15` → 0 marks; fewer than five
words with `keyword < 0.2` → 0 marks. If the model answer produces no keywords,
the keyword weight is redistributed instead of granting full marks.

Weights and thresholds live in the database and can be changed at
**Admin → Settings**; saving triggers `/api/settings/rescore`, which recomputes
totals from the stored component scores instantly (no NLP re-run).

### AI-generated-answer detection

With `requirements-ai.txt` installed, detection uses **distilgpt2** perplexity
plus sentence-level burstiness and a ChatGPT-phrase list
(`prob = ppl·0.65 + burstiness·0.30 + phrases·0.05`). Without it, a heuristic
(bigram perplexity, vocabulary richness, formality, uniformity, …) is used
instead. Verdicts: ≥ 45% AI, 25–45% uncertain, < 25% likely human
(configurable via `AI_FLAG_THRESHOLD` / `AI_REVIEW_THRESHOLD`). Results are a
statistical signal, not proof.

### Plagiarism detection

- **Lexical (decision)** — TF-IDF cosine over word 1–2 grams per question, with
  the threshold from Admin → Settings (default 60%). This is what flags a pair.
- **Semantic (review)** — `all-MiniLM-L6-v2` embeddings. Pairs above
  `PLAGIARISM_SEMANTIC_REVIEW_GATE` (0.90) that are *not* lexically flagged are
  returned with `semantic_review: true` and shown as "possible paraphrase —
  review" in the UI, because independent answers to the same question are often
  semantically 0.9+ similar.

---

## 7. Project layout

```
smart-exam-checker/
├── .github/workflows/ci.yml      backend + frontend CI
├── backend/
│   ├── app/
│   │   ├── api/          auth, users, subjects, exams, questions, answers,
│   │   │                 dashboard, export, settings, advanced_nlp
│   │   ├── core/         security (PyJWT + bcrypt), deps (role guards)
│   │   ├── models/       user, subject, exam, question, answer(+score), settings
│   │   ├── nlp/          scorer, similarity, keyword_extractor, grammar_checker,
│   │   │                 tokenizer, embeddings + advanced/ (ai_detector,
│   │   │                 plagiarism_detector, rubric_grader, class_intelligence,
│   │   │                 feedback_generator, model_answer_gen)
│   │   ├── files.py      authenticated /api/files serving
│   │   ├── limiter.py    shared rate limiter
│   │   ├── seed.py       demo data (also runnable via `python -m app.seed`)
│   │   └── main.py       FastAPI app
│   ├── alembic/versions/0001_initial_schema.py
│   ├── tests/            auth, answers, exams, nlp, security, plagiarism
│   ├── pytest.ini, ruff.toml, requirements*.txt, Dockerfile, .env.example
└── frontend/
    ├── src/app/(auth)/login, (dashboard)/{admin,teacher,student}
    ├── src/components/{charts,layout,providers,shared,ui}
    ├── src/lib/{api,utils,exam-results}, src/store/authStore.ts
    └── next.config.ts, eslint.config.mjs, tsconfig.json
```

### Data model

`users` (role, `token_version`) → `subjects` → `exams` (availability window) →
`questions` (model answer, keywords) → `student_answers` (unique per student per
question) → `scores` (component scores, feedback, override audit) plus the
`app_settings` key/value table.

---

## 8. API overview

All routes are prefixed with `/api` (docs: `/docs`).

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register` (admin), `/auth/login`, `/auth/refresh`, `/auth/logout`, `GET /auth/me`, `PUT /auth/change-password` |
| Users | `GET/POST /users/`, `POST /users/bulk-import`, `GET/PUT/DELETE /users/{id}`, `PUT /users/{id}/activate`, `PUT /users/{id}/profile-photo` |
| Subjects / Exams / Questions | CRUD with ownership checks; students see active exams inside their window, without model answers |
| Answers | `POST /answers/submit`, `POST /answers/submit-exam`, `GET /answers/` (scoped), `/answers/my-answers`, `/answers/question/{id}`, `PUT /answers/score/{id}/override` |
| Dashboards | `GET /dashboard/student`, `/dashboard/teacher`, `/dashboard/admin` |
| Export | `GET /export/results/{exam_id}` (CSV), `/xlsx`, `/pdf` |
| Settings | `GET /settings` (authenticated), `PUT /settings/weights`, `PUT /settings/{key}`, `POST /settings/rescore` (admin) |
| Advanced NLP | `POST /nlp/plagiarism-check`, `/nlp/ai-auto-scan`, `/nlp/ai-detection`, `/nlp/rubric-grade`, `/nlp/generate-model-answer`, `/nlp/class-report`, `GET /nlp/feedback/{answer_id}` — teacher/admin only |
| Files | `GET /api/files/{path}` (Bearer or `?token=`) |
| Ops | `GET /health`, `/health/db`, `/health/nlp`, `/health/system` (admin), `WS /ws/grade/{user_id}?token=` |

---

## 9. Deployment

Two parts, deployed separately:

| Part | Where | Why |
|---|---|---|
| Frontend | **Vercel** | Next.js CDN + SSR |
| Backend | VPS / Docker (PM2 config included) | spaCy + torch + SQLite/PostgreSQL, optional Java for LanguageTool |

### Backend

```bash
cd backend
export ENVIRONMENT=production
export JWT_SECRET=$(python -c "import secrets;print(secrets.token_urlsafe(48))")
export DATABASE_URL=postgresql://user:pass@host:5432/smart_exam_db
export BACKEND_CORS_ORIGINS='["https://your-frontend.example.com"]'
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

`ecosystem.config.js` runs it under PM2 on `127.0.0.1:8090` (2 GB memory
headroom for the AI models) and the frontend on `127.0.0.1:3090`.

> Run a single worker: the WebSocket connection registry and the rate limiter are
> in-process. Scale out only after moving that state to a shared store.

### Frontend on Vercel

- Root directory: `frontend`
- Build command: `npm run build`
- Environment variable: `NEXT_PUBLIC_API_URL=https://your-backend.example.com/api`

### Docker

```bash
cd backend
docker build -t smart-exam-backend .
# with AI detection + embeddings:
docker build --build-arg INSTALL_AI_DEPS=true -t smart-exam-backend .
docker run -p 8000:8000 -e JWT_SECRET=... -e ENVIRONMENT=production smart-exam-backend
```

The image installs Java (for LanguageTool), pre-downloads the spaCy and embedding
models, runs as a non-root user and has a `/health` healthcheck.

---

## 10. Troubleshooting

- **401 on every request** — the token was revoked (logout/password change) or
  expired; sign in again. If the API restarted with a new random secret and no
  `.env`, previously issued tokens are invalid too: `backend/.jwt_secret` keeps
  the secret stable across restarts.
- **Login fails / CORS error in the browser** — check that the backend is on
  :8000 and that the frontend origin is listed in `BACKEND_CORS_ORIGINS`
  (in production there are no allowed origins until you set it).
- **429 Too Many Requests** — you hit the rate limit (10/min on login). Wait a
  minute or set `RATE_LIMIT_ENABLED=false` while developing.
- **spaCy / sentence-transformers slow on first request** — the models download
  on first use (~13 MB spaCy, ~90 MB MiniLM, ~330 MB distilgpt2). Pre-download
  them (the Dockerfile does) or install `requirements-ai.txt`.
- **Charts look unstyled** — stop both servers, `npm install`, restart.
- **Start over with a clean database** — delete `backend/smart_exam.db` and
  restart the backend (or run `python -m app.seed`).

---

## 11. Known limitations

- Grading is lexical/statistical: short or technical answers can score lower or
  higher than a human would judge. It is a grading *aid*, not a substitute.
- Semantic plagiarism similarity is a review signal only; paraphrased copies
  with no lexical overlap are surfaced for manual review rather than flagged.
- AI-generated-text detection is probabilistic and can misjudge very regular
  prose; answers under ~20 characters are never flagged.
- Rate limiting and WebSocket connections are per-process (single worker).
