# FitCheck AI — Complete Setup & Run Guide

This guide walks you through running the full FitCheck AI project from scratch.
No experience needed — follow each step exactly.

---

## What You'll Set Up

| Part | What it is |
|------|-----------|
| Frontend | The website (HTML file — opens in browser) |
| Backend  | The Python server (FastAPI) |
| Database | Supabase PostgreSQL (free) |
| Redis    | Rate limiting (local or Upstash free) |
| AI       | HuggingFace CatVTON (free) |

---

## PART 1 — Install Requirements on Your Computer

### Step 1 — Install Python

1. Go to **python.org/downloads**
2. Download Python **3.12** (not 3.13, not 3.11 — exactly 3.12)
3. Run the installer
4. ✅ **IMPORTANT:** Check the box **"Add Python to PATH"** during install
5. After install, open Command Prompt (Windows) or Terminal (Mac/Linux) and verify:
   ```
   python --version
   ```
   You should see: `Python 3.12.x`

---

### Step 2 — Install Git

1. Go to **git-scm.com/downloads**
2. Download and install Git (default settings are fine)
3. Verify:
   ```
   git --version
   ```

---

### Step 3 — Install Redis (for rate limiting)

**Windows:**
1. Go to **github.com/microsoftarchive/redis/releases**
2. Download `Redis-x64-3.0.504.msi`
3. Install it (default settings)
4. Redis will run as a background service automatically

**Mac:**
```
brew install redis
brew services start redis
```

**Linux (Ubuntu):**
```
sudo apt install redis-server
sudo systemctl start redis
```

Verify Redis is running:
```
redis-cli ping
```
Should reply: `PONG`

---

## PART 2 — Set Up the Backend

### Step 4 — Unzip and Open the Backend

1. Unzip `fitcheck_backend.zip` to a folder, e.g. `C:\Projects\fitcheck_backend`
2. Open your terminal / command prompt
3. Navigate to the folder:
   ```
   cd C:\Projects\fitcheck_backend
   ```
   (Mac/Linux: `cd /home/yourname/fitcheck_backend`)

---

### Step 5 — Create a Virtual Environment

A virtual environment keeps the project's packages separate from your system Python.

```
python -m venv venv
```

Now **activate** it:

**Windows:**
```
venv\Scripts\activate
```

**Mac / Linux:**
```
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal line. This means it's active.

> ⚠️ Every time you open a new terminal to work on this project, you must activate the venv again.

---

### Step 6 — Install Python Packages

With the venv active:

```
pip install -r requirements.txt
```

This installs all packages (FastAPI, SQLAlchemy, etc.). It takes 2–5 minutes.

---

### Step 7 — Set Up Supabase (Free Database)

1. Go to **supabase.com** → Sign up (free, no credit card)
2. Click **New Project**
3. Enter:
   - Name: `fitcheck`
   - Database Password: choose a strong password (save it!)
   - Region: `Southeast Asia (Singapore)` — closest to India
4. Wait ~2 minutes for the project to be created
5. Go to **Settings → Database**
6. Scroll to **Connection string** → select **URI**
7. Copy the connection string — it looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```
8. Keep this — you'll need it in Step 9

---

### Step 8 — Get a HuggingFace Token (Free AI)

1. Go to **huggingface.co** → Sign up (free)
2. Go to your Profile → **Settings → Access Tokens**
3. Click **New token** → name it `fitcheck` → Role: `Read`
4. Copy the token (starts with `hf_...`)

> This token is optional but gives you priority in the AI queue. Without it, the free AI still works but may be slower.

---

### Step 9 — Create Your .env File

In the `fitcheck_backend` folder, create a new file called `.env` (not `.env.example` — a new file).

**Windows:** Right-click → New → Text Document → rename to `.env`
**Mac/Linux:** `touch .env`

Open it and paste this, filling in YOUR values:

```
DEBUG=True
SECRET_KEY=fitcheck_secret_key_change_this_in_production_2024

# Supabase database (from Step 7)
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT].supabase.co:5432/postgres

# Redis (local)
REDIS_URL=redis://localhost:6379

# HuggingFace (from Step 8)
HUGGINGFACE_TOKEN=hf_your_token_here
HF_SPACE_URL=https://zhengchong-liu-catvton.hf.space

# Replicate — leave blank for now (only needed for paid credits)
REPLICATE_API_TOKEN=

# Cloudflare R2 — leave blank for now (images use placeholder)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_ENDPOINT_URL=
S3_BUCKET=fitcheck-uploads

# Email — leave blank for now (emails are skipped, app still works)
RESEND_API_KEY=
FROM_EMAIL=noreply@fitcheck.ai

# Razorpay — leave blank for now (uses demo/mock mode)
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=

# Rate limits
FREE_DAILY_TRYON_LIMIT=3
```

> ✅ Replace `[YOUR-PASSWORD]` and `[YOUR-PROJECT]` with your actual Supabase values.
> Everything else can stay blank for now — the app works in demo mode.

---

### Step 10 — Run Database Migrations

This creates all the tables in your Supabase database automatically.

Make sure your venv is active, then run:

```
alembic upgrade head
```

You should see output like:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial, Initial migration
```

If you see an error about connection — double-check your `DATABASE_URL` in `.env`.

---

### Step 11 — Start the Backend Server

```
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     FitCheck AI backend starting...
INFO:     Database ready
INFO:     Uvicorn running on http://127.0.0.1:8000
```

✅ **Backend is running!**

- API is live at: **http://localhost:8000**
- Interactive docs at: **http://localhost:8000/docs**

> The `--reload` flag means the server auto-restarts whenever you change code.
> To stop the server: press `Ctrl + C`

---

## PART 3 — Run the Frontend

### Step 12 — Open the Frontend

1. Find the file `fitcheck_ai_complete.html`
2. Double-click it to open in your browser

That's it! The frontend is a single HTML file — no server needed.

> **Chrome or Edge recommended.** Firefox works too.

---

## PART 4 — Test That Everything Works

### Step 13 — Test the API

Open your browser and go to:
```
http://localhost:8000/health
```

You should see:
```json
{"status": "ok", "version": "1.0.0"}
```

Open the interactive API docs:
```
http://localhost:8000/docs
```

You can test every endpoint directly in the browser here.

---

### Step 14 — Test Registration

In the API docs (`/docs`):

1. Click **POST /api/v1/auth/register**
2. Click **Try it out**
3. Enter:
   ```json
   {
     "email": "test@example.com",
     "password": "Test1234",
     "full_name": "Test User"
   }
   ```
4. Click **Execute**
5. You should get back an `access_token` and `refresh_token`

---

### Step 15 — Test the Frontend

1. Open `fitcheck_ai_complete.html` in your browser
2. Click **Try Now** → Accept terms → Solve CAPTCHA
3. In the studio:
   - Upload any photo of a person
   - Paste any product image URL (or upload a product image)
   - Click **Generate Free (3/day)**
4. Watch the loading animation with AI status messages
5. See the result!

> In demo mode (no Replicate key), you'll get a placeholder result image.
> With a HuggingFace token, it will call the real AI — takes 30–60 seconds.

---

## PART 5 — Common Issues & Fixes

### "ModuleNotFoundError"
Your venv isn't active. Run:
```
venv\Scripts\activate     # Windows
source venv/bin/activate  # Mac/Linux
```

### "Connection refused" on database
Your Supabase URL is wrong. Go back to Supabase → Settings → Database and copy the URI again. Make sure you replaced `[YOUR-PASSWORD]` with your actual password.

### "Redis connection refused"
Redis isn't running. Start it:
```
redis-server          # Mac/Linux
# Windows: it should run as a service. Check Services app.
```

### "Permission denied" on venv (Mac/Linux)
```
chmod +x venv/bin/activate
source venv/bin/activate
```

### Backend starts but AI doesn't work
That's fine for now — AI requires HuggingFace token. Add it to `.env` and restart the server.

### Frontend shows placeholder result instead of real AI
This is expected in demo mode. The real AI (HuggingFace CatVTON) runs in the backend. The frontend will show real results once you connect it to the backend via the API.

---

## PART 6 — Running It Every Day

Once set up, to start the project each time:

**Step A — Start Redis** (if not running as a service):
```
redis-server
```

**Step B — Open a new terminal, activate venv, start backend:**
```
cd C:\Projects\fitcheck_backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Step C — Open the frontend:**
Double-click `fitcheck_ai_complete.html`

---

## PART 7 — Optional: Add Real Services Later

When you're ready to make it fully real:

| Service | What to do |
|---------|-----------|
| **Cloudflare R2** | Add keys to `.env` — images upload to cloud instead of placeholder |
| **Replicate** | Add token to `.env` — paid credits use best quality AI |
| **Resend** | Add key to `.env` — welcome emails start working |
| **Razorpay** | Add keys to `.env` — real payments replace demo mode |

For each one, after adding to `.env`:
```
Ctrl+C    (stop server)
uvicorn app.main:app --reload --port 8000    (restart)
```

---

## Quick Reference — All Commands

```bash
# First time setup
python -m venv venv
source venv/bin/activate    # or: venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head

# Every time you want to run
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v

# Check API is working
curl http://localhost:8000/health
```

---

## Project Structure (for reference)

```
fitcheck_backend/
├── .env                    ← Your secret keys (create this, never share it)
├── .env.example            ← Template showing what .env needs
├── requirements.txt        ← All Python packages
├── app/
│   ├── main.py             ← Server entry point
│   ├── api/
│   │   ├── auth.py         ← Login, register, Google OAuth
│   │   ├── tryon.py        ← Core try-on endpoint
│   │   ├── credits.py      ← Buy credits, balance, history
│   │   ├── users.py        ← Profile management
│   │   ├── products.py     ← URL scraper
│   │   └── admin.py        ← Admin controls
│   ├── core/
│   │   ├── config.py       ← Reads from .env
│   │   ├── database.py     ← PostgreSQL connection
│   │   ├── security.py     ← JWT tokens, passwords
│   │   └── rate_limiter.py ← Redis rate limiting
│   ├── models/
│   │   ├── user.py         ← User + credits DB table
│   │   ├── tryon.py        ← Try-on DB table
│   │   └── product.py      ← Product cache table
│   └── services/
│       ├── ai_service.py   ← HuggingFace + Replicate routing
│       ├── storage_service.py ← Image uploads
│       ├── product_service.py ← Web scraper
│       └── email_service.py   ← Welcome emails
├── migrations/
│   └── 001_initial.py      ← Creates all DB tables
└── tests/
    └── test_api.py         ← API tests
```

---

**Need help?** Every error message tells you exactly what's wrong.
Read it carefully — 90% of issues are either a wrong URL in `.env` or the venv not being activated.
