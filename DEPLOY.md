# Deploying

Two pieces:

| Piece | Host | Why |
|---|---|---|
| Next.js frontend (`frontend/`) | **Vercel** | Native Next.js, free |
| FastAPI modeling API (`backend/`) | **Render** | statsmodels + scipy + pandas ≈ 275 MB — over Vercel's serverless limit, needs a real Python server |

Saved models (the Compare tab) are stored in the visitor's **browser** (localStorage) — no database to run.

Deploy the backend first so you have its URL for the frontend's env var.

---

## 1 · Backend → Render

1. **New → Blueprint** at <https://dashboard.render.com>, connect the GitHub repo. Render reads `render.yaml` and creates a free web service **`sports-lab-api`** (root `backend/`, installs `requirements-api.txt`, runs `uvicorn main:app`).
   *Or* create the service by hand: Root Directory `backend`, Build `pip install -r requirements-api.txt`, Start `uvicorn main:app --host 0.0.0.0 --port $PORT`, Health check `/api/health`, env var `PYTHON_VERSION=3.11.9`.
2. Wait for the deploy. Note the URL, e.g. `https://sports-lab-api.onrender.com`.
3. Check it: `https://sports-lab-api.onrender.com/api/health` → `{"ok":true}`.

The built research dataset is committed under `backend/data/real/`, so the API serves real data immediately — no scrape, no Census download.

**Free-tier note:** the service sleeps after ~15 min idle; the first request after a nap takes ~30–50 s to wake, then it's fast. The app calls the API directly from the browser (not proxied through Vercel), so it waits this out gracefully. To keep it warm, add a cron ping to `/api/health` (e.g. cron-job.org) or upgrade to a paid instance.

---

## 2 · Frontend → Vercel

1. **Add New → Project** at <https://vercel.com/new>, import the same repo.
2. **Root Directory: `frontend`** (Vercel then auto-detects Next.js).
3. **Environment Variable** (all environments):
   ```
   NEXT_PUBLIC_API_URL = https://sports-lab-api.onrender.com
   ```
   This is read at build time — set it before the first deploy (or redeploy after adding it).
4. Deploy. Done.

---

## Local development is unchanged

```bash
npm run setup   # backend venv + full requirements.txt + frontend deps
npm run dev     # API :8000 + web :3000
```

With `NEXT_PUBLIC_API_URL` unset, the frontend uses relative `/api/*` paths and `next.config.mjs` proxies them to `localhost:8000`.

## Redeploys

- Push to `main` → Render redeploys the API automatically; Vercel redeploys the frontend automatically.
- `render.yaml` / `backend/requirements-api.txt` only affect the API; `frontend/` only affects Vercel.
