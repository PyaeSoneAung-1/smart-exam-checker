# Smart Exam Answer Checker

Modern exam-grading platform: teachers create exams, students answer in their own
words, and an NLP engine scores answers (keyword / semantic similarity / grammar /
completeness). Admin, Teacher and Student dashboards each get animated stat cards
and live diagrams (donut, bar, area, radial gauge) that recompute from the database.

This build adds:

- A polished **Dark / Light theme** with a smooth color-fade transition on toggle
  and a restrained indigo accent palette (no rainbow).
- **Animated, diagram-rich dashboards** for every role (Admin / Teacher / Student).
- **3 new students** who have already taken both exams:
  `San Lin Aung`, `Swan Yee Htut`, `Thura Hein`.
- Admin & Teacher dashboards automatically reflect the new students' results
  (the dashboards aggregate live from the DB).

---

## 1. Prerequisites

| Tool | Version |
|------|---------|
| Node.js | 18.18+ (20+ recommended) |
| npm | 9+ |
| Python | 3.10 – 3.12 |
| pip / venv | standard |

No PostgreSQL or Redis required for local dev — the backend defaults to **SQLite**
(the `smart_exam.db` file). Redis/Celery are optional and only used for caching.

---

## 2. Backend — run it

```bash
cd backend

# (a) create & activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# (b) install dependencies
pip install -r requirements.txt

#    (optional) download the spaCy model used by the NLP scorer
python -m spacy download en_core_web_sm

# (c) run the API  (http://localhost:8000)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On startup the app **automatically seeds the database** (see `app/seed.py`):

- Creates admin, 2 teachers, 2 students, 2 subjects, 2 exams, 10 questions.
- **Adds the 3 extra students and their exam answers** (idempotent — runs only
  once; safe to restart).
- API docs: <http://localhost:8000/docs>

> The shipped `smart_exam.db` already contains the original 2 students; the first
> backend start will add the 3 new students + their graded answers to it.

---

## 3. Frontend — run it

```bash
cd frontend

# (a) install dependencies
npm install

# (b) start the dev server  (http://localhost:3000)
npm run dev
```

Then open <http://localhost:3000> and log in.

`frontend/.env` is pre-set for local dev:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

Production build (optional):
```bash
npm run build
npm run start
```

---

## 4. Login credentials (password is `123456` for everyone)

| Role    | Name              | Email                       |
|---------|-------------------|-----------------------------|
| Admin   | System Admin      | admin@smartexam.com         |
| Teacher | Daw Ni Lar Win    | dawnilarwin@gmail.com       |
| Teacher | Daw Nwe Ni Win    | dawnweniwin@gmail.com       |
| Student | Pyae Sone Aung    | pyaesoneaung@gmail.com      |
| Student | Pyae Myat Phyo    | pyaemyatphyo@gmail.com      |
| Student | San Lin Aung      | sanlinaung@gmail.com        | ← new
| Student | Swan Yee Htut     | swanyeehtut@gmail.com       | ← new
| Student | Thura Hein        | thurahein@gmail.com         | ← new

All passwords: `123456`

---

## 5. What the new students do

The 3 new students each **answered all 10 questions across both exams**
(Business English + Cyber Security), with pre-computed NLP-style scores so their
results appear immediately:

- **San Lin Aung** — high performer
- **Swan Yee Htut** — medium performer
- **Thura Hein** — lower performer

Because every dashboard reads live from the database:

- **Admin** dashboard: total students (5), submissions (50), average system score,
  user-breakdown donut and platform-activity bar chart all update.
- **Teacher** dashboards: each teacher sees the new students in *Recent
  Submissions*, in *Subject Performance*, and in the average-class-score gauge.
- **Student** dashboard: log in as any new student to see their own average /
  highest / lowest, subject-performance bar chart and recent-scores trend.

---

## 6. Theme

Use the sun/moon button (top-right of the navbar) to toggle **Dark / Light**.
The whole UI fades smoothly between themes; charts recolor automatically.

---

## 7. Project layout

```
smart-exam-checker/
├── backend/
│   ├── app/
│   │   ├── api/        auth, users, subjects, exams, questions, answers, dashboard, …
│   │   ├── core/       config, security, deps
│   │   ├── models/     user, subject, exam, question, answer
│   │   ├── nlp/        scorer, similarity, keyword, grammar + advanced/
│   │   ├── schemas/    pydantic models
│   │   ├── seed.py     ← demo data + 3 new students
│   │   └── main.py     FastAPI app (runs seed on startup)
│   ├── requirements.txt
│   └── .env            ← local SQLite config
└── frontend/
    ├── src/
    │   ├── app/                 Next.js App Router pages (admin / teacher / student)
    │   ├── components/
    │   │   ├── charts/          ModernCharts.tsx, useChartColors.ts (theme-aware)
    │   │   ├── layout/          Navbar (theme toggle), Sidebar, DashboardLayout
    │   │   ├── shared/          motion.tsx, StatsCard, …
    │   │   └── ui/              shadcn/ui primitives
    │   ├── lib/api.ts           axios client + endpoint groups
    │   ├── store/authStore.ts   zustand auth
    │   └── app/globals.css      ← theme palette + transitions
    ├── package.json
    └── .env             ← NEXT_PUBLIC_API_URL
```

---

## 8. Troubleshooting

- **Login fails / 401**: make sure the backend is running on :8000 and
  `NEXT_PUBLIC_API_URL` in `frontend/.env` matches.
- **Charts look unstyled**: stop both servers, `npm install` again, restart.
- **spaCy / sentence-transformers slow on first run**: the NLP models download on
  first use; this only affects live answer scoring, not the seeded demo data.
- **Want a clean database**: delete `backend/smart_exam.db` and restart the
  backend — the full seed (all 5 students + exams) runs from scratch.

---

## 9. Deployment (Vercel + API host)

This project has **two parts** — the Next.js frontend and the FastAPI backend
(which bundles spaCy / scikit-learn / Java-based LanguageTool for NLP grading).
They are deployed separately:

| Part    | Where it runs        | Why                                                        |
|---------|----------------------|------------------------------------------------------------|
| Frontend | **Vercel**           | Next.js is a first-class Vercel citizen (CDN + SSR).       |
| Backend  | VPS / Docker host    | Heavy ML dependencies + SQLite file DB + optional WebSocket don't fit Vercel serverless. |

### Frontend → Vercel

1. Push the repo to GitHub, then **Import** it in Vercel.
2. In the project settings set:
   - **Framework Preset:** Next.js (auto-detected)
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build` (default)
3. Add the environment variable (build time):

   ```bash
   NEXT_PUBLIC_API_URL=https://exam.hiroshi.cloud/api
   ```

   This tells the browser to call the backend through the public API URL. The
   backend currently allows all CORS origins, so no extra CORS config is needed.

4. Deploy. The app is fully client-side for auth (JWT in `localStorage`), so no
   server-side env secrets are required on Vercel.

### Backend (stays on your host)

The backend keeps running as-is, e.g. via PM2:

```bash
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8090
```

On first start it creates and seeds a fresh `smart_exam.db` automatically
(admin, 2 teachers, 5 students, 2 exams, 10 questions, 50 graded answers —
passwords are all `123456`).

> If you ever want the backend on a cloud too, it can be containerized with the
> included `backend/Dockerfile` and run on Railway / Render / Fly.io with a
> PostgreSQL `DATABASE_URL`.
