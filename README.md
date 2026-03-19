# FitCheck AI

AI-powered virtual try-on platform. Upload your photo + any product → see how it looks on you.

## Project Structure

```
fitcheck_ai/
├── frontend/
│   └── index.html          ← The complete website (open in browser)
├── backend/
│   ├── .env.example        ← Copy this to .env and fill in your keys
│   ├── requirements.txt    ← Python packages
│   ├── alembic.ini         ← Database migration config
│   ├── app/
│   │   ├── main.py         ← FastAPI server entry point
│   │   ├── api/            ← All API endpoints
│   │   ├── core/           ← Config, database, security, rate limiter
│   │   ├── models/         ← Database table definitions
│   │   └── services/       ← AI, storage, email, scraper
│   ├── migrations/         ← Database schema (auto-creates tables)
│   └── tests/              ← API tests
└── SETUP_GUIDE.md          ← Full step-by-step setup instructions
```

## Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in your values
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Open `frontend/index.html` in your browser.

**Read `SETUP_GUIDE.md` for full instructions including Supabase, HuggingFace, and all services.**

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Pure HTML/CSS/JS (no framework, no build step) |
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL via Supabase (free) |
| Cache | Redis (rate limiting) |
| AI Free | HuggingFace CatVTON (₹0) |
| AI Paid | Replicate IDM-VTON (credits system) |
| Storage | Cloudflare R2 (free 10GB) |
| Email | Resend (free 3000/month) |
| Payments | Razorpay (credit top-ups) |
