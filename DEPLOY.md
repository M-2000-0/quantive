# Vercel Deployment Guide

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Vercel Project 1: Frontend (React/Vite)        │
│  your-app.vercel.app                            │
└──────────────────────┬──────────────────────────┘
                       │ API calls
┌──────────────────────▼──────────────────────────┐
│  Vercel Project 2: Backend (FastAPI)            │
│  your-app-api.vercel.app                        │
│  └── PostgreSQL (Vercel Postgres / Neon / Supa) │
└─────────────────────────────────────────────────┘
```

Two separate Vercel projects: one for the React frontend, one for the FastAPI backend.

---

## Prerequisites

1. **Vercel account** ( Hobby is fine for testing )
2. **PostgreSQL database** — use one of:
   - [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres) (recommended — free tier available)
   - [Neon](https://neon.tech) (free tier, great for staging)
   - [Supabase](https://supabase.com) (free tier)
3. **Stripe account** (for Qubo Tax billing)
4. **GitHub repo** connected to Vercel

---

## Step 1: Set Up PostgreSQL

### Option A: Vercel Postgres (Recommended)
1. Go to your Vercel dashboard → Storage → Create Database → Postgres
2. Copy the **Transaction mode** pooler URL (required for serverless)
3. It looks like: `postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require`

### Option B: Neon
1. Create a free project at [neon.tech](https://neon.tech)
2. Copy the connection string from the dashboard

### Option C: Supabase
1. Create a free project at [supabase.com](https://supabase.com)
2. Go to Settings → Database → Connection string → Transaction mode

---

## Step 2: Deploy Backend to Vercel

### 2a. Create a new Vercel project for the backend

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repo
3. **Root Directory**: `backend`
4. **Framework Preset**: Other
5. Click **Deploy** (it will fail first time — that's expected, we need env vars)

### 2b. Set Environment Variables

Go to **Settings → Environment Variables** and add:

| Variable | Value | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | Use **Transaction mode** URL |
| `PERSONAL_DATABASE_URL` | `postgresql://...` | Can share same DB |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` | Generate a random key |
| `ENVIRONMENT` | `production` | |
| `SECURE_COOKIES` | `true` | |
| `CORS_ORIGINS` | `https://your-frontend.vercel.app` | Your frontend URL |
| `LOG_LEVEL` | `INFO` | |
| `RATE_LIMIT_PER_MINUTE` | `2000` | |

### 2c. Add Stripe variables (if using Qubo billing)

| Variable | Value |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` |
| `STRIPE_QUBO_STARTER_MONTHLY_PRICE_ID` | `price_...` |
| `STRIPE_QUBO_STARTER_YEARLY_PRICE_ID` | `price_...` |
| `STRIPE_QUBO_PRO_MONTHLY_PRICE_ID` | `price_...` |
| `STRIPE_QUBO_PRO_YEARLY_PRICE_ID` | `price_...` |
| `STRIPE_QUBO_SOVEREIGN_MONTHLY_PRICE_ID` | `price_...` |
| `STRIPE_QUBO_SOVEREIGN_YEARLY_PRICE_ID` | `price_...` |

### 2d. Redeploy

Go to **Deployments** → click **Redeploy** on the latest deployment.

### 2e. Initialize Database Tables

After first successful deploy, visit:
```
https://your-app-api.vercel.app/api/health
```

Tables are auto-created by SQLAlchemy on first request. If not, run:
```bash
# From your local machine with the production DATABASE_URL
cd backend
DATABASE_URL="postgresql://..." python -c "from app.database import engine, Base; from app.models import *; Base.metadata.create_all(engine)"
```

---

## Step 3: Deploy Frontend to Vercel

### 3a. Create a new Vercel project for the frontend

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import the **same GitHub repo**
3. **Root Directory**: `frontend`
4. **Framework Preset**: Vite
5. **Build Command**: `npm run build`
6. **Output Directory**: `dist`

### 3b. Set Environment Variables

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://your-app-api.vercel.app` |

### 3c. Deploy

Click **Deploy**. The frontend will build and deploy automatically.

---

## Step 4: Configure Custom Domains (Optional)

### Backend
1. Go to backend project → Settings → Domains
2. Add `api.yourdomain.com`
3. Update `CORS_ORIGINS` env var to include the frontend domain

### Frontend
1. Go to frontend project → Settings → Domains
2. Add `yourdomain.com`
3. Update DNS as instructed by Vercel

---

## Step 5: Set Up Stripe Webhooks

1. Go to [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks)
2. Add endpoint: `https://your-app-api.vercel.app/api/billing/webhook`
3. Select events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
4. Copy the webhook signing secret to `STRIPE_WEBHOOK_SECRET`

---

## Local Development

```bash
# Frontend (port 5173, proxies /api to backend)
cd frontend
npm run dev

# Backend (port 8000)
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Frontend proxies `/api` to `localhost:8000` automatically via `vite.config.ts`.

---

## Important Notes

### Database
- **Must use PostgreSQL** in production — SQLite doesn't work in Vercel serverless (ephemeral filesystem)
- Use **Transaction mode** connection pooling (not Session mode) for Vercel/Neon/Supabase
- Connection string format: `postgresql://user:pass@host:port/db?sslmode=require`

### File Uploads
- Vercel serverless functions have a **10MB body limit** and **30s timeout** (configurable to 60s on Pro)
- Tax document uploads work within these limits (10MB max per file)
- Files stored in `/tmp` on serverless (ephemeral) — for persistent storage, use S3/R2

### Cold Starts
- First request to backend may take 5-10s (Python cold start)
- Subsequent requests are fast (< 200ms)
- Vercel Pro plan reduces cold starts with "Fluid Functions"

### Environment Variables
- Frontend: `VITE_*` vars are baked into the build at build time
- Backend: All env vars are read at runtime from Vercel settings
