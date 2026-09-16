# Smart Exam Checker — frontend

Next.js 16 (App Router) + React 19 + TypeScript + Tailwind v4 UI for the
Smart Exam Answer Checker. See the [project README](../README.md) for the full
architecture, backend setup and deployment guide.

## Run

```bash
npm install
printf 'NEXT_PUBLIC_API_URL=http://localhost:8000/api\n' > .env   # or leave unset to use the dev proxy
npm run dev                                                     # http://localhost:3000
```

## Scripts

| Script | Purpose |
|---|---|
| `npm run dev` | Development server (Turbopack) |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run lint` | ESLint (no warnings allowed) |
| `npm run typecheck` | `tsc --noEmit` |

## Structure

- `src/app/(auth)/login` — sign-in
- `src/app/(dashboard)/{admin,teacher,student}` — role dashboards
  (users/exams/subjects/settings, marks/plagiarism/AI detection/export, exams/results/profile)
- `src/components/` — `charts` (recharts wrappers), `layout` (navbar/sidebar),
  `shared`, `ui` (Base UI + shadcn-style primitives), `providers`
- `src/lib/api.ts` — axios client, typed endpoint groups, `fileUrl()` helper for
  authenticated uploads
- `src/store/authStore.ts` — zustand session store (persisted)

Auth is client-side: the access token lives in the persisted zustand store and is
attached by the axios interceptor; a 401 clears the session and returns to login.
Uploaded files are fetched with `?token=` because `<img>` cannot send headers.
