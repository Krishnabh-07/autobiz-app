# 💪 AutoBiz AI — Universal Business Automation SaaS

Turn any business into an **autopilot machine**. Multi-tenant SaaS platform for Indian small businesses (gyms, clinics, salons, dental, coaching, etc.).

- **Leads CRM** — capture & nurture leads via public storefront
- **Members / Patients** — management with attendance & QR passes
- **Payments & Invoices** — fee tracking, renewals, defaulter detection
- **24/7 WhatsApp AI automation** — automated reminders, trial follow-ups, expiry nudges
- **Customer Portal** — members check status, attendance, invoices
- **Super Admin "God Mode"** — platform-wide oversight for the owner (@Krishnabh)

> 💡 Revenue model: ₹1,500/month per business, 14-day free trial.

---

## 🏗 Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt |
| Automation | APScheduler (daily WhatsApp jobs) |
| WhatsApp | Meta Cloud API (Graph v20.0) with simulated fallback |
| AI | Google Gemini (optional) · rule-based Hinglish fallback |
| Frontend | Plain HTML + Tailwind CDN + vanilla JS (no build step) |
| Database | PostgreSQL (production) · SQLite (local) |
| Deploy | Railway (Nixpacks) |

---

## 🚀 Local Development

### 1. Setup

```bash
# From repo root
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate    # macOS/Linux

pip install -r requirements.txt

# Optional: create .env from template
Copy-Item .env.example .env   # Windows PowerShell
# cp .env.example .env        # macOS/Linux
```

### 2. Run

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://127.0.0.1:8000** — the API and all frontend pages are served from the same app.

### 3. Test super admin (God Mode)

```bash
curl -H "x-admin-key: krishnabh_god_mode_2024_secret" http://127.0.0.1:8000/superadmin/overview
```

---

## 🧩 Project Structure

```
backend/
├── main.py            # Monolith app: 84 routes + serves frontend
├── models.py          # 16 SQLAlchemy models
├── schemas.py         # ~50 Pydantic DTOs
├── auth.py            # JWT + bcrypt auth
├── admin.py           # Super Admin /superadmin/* routes
├── bot_ai.py          # Hinglish WhatsApp template engine
├── whatsapp_routes.py # /whatsapp/* reminder endpoints
├── whatsapp_cloud.py  # Meta WhatsApp Cloud API dispatcher
├── scheduler.py       # APScheduler daily jobs
├── database.py        # Engine/session (Postgres/SQLite)
├── reset_db.py        # ⚠️ DEV ONLY — wipes all data
└── clear_data.py      # ⚠️ DEV ONLY — wipes SQLite data
frontend/
├── index.html               # Landing page + login/OTP
├── dashboard.html           # "Business OS" owner dashboard
├── customer_portal.html     # Member portal
├── business_storefront.html # Public storefront (/b/{id})
├── explore.html             # Explore nearby businesses
├── superadmin.html          # God Mode 👑
├── support.html             # Support/contact
├── privacy.html / terms.html
└── manifest.json / sw.js    # PWA
```

---

## ☁️ Production (Railway)

1. Push to GitHub → create project on [Railway](https://railway.app) → deploy.
2. Set the following env vars in Railway:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Railway Postgres plugin URL |
| `SECRET_KEY` | Long random string (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `SUPER_ADMIN_KEY` | Your private God Mode key |
| `SITE_BASE_URL` | `https://<your-app>.up.railway.app` |
| `ALLOWED_ORIGINS` | `*` or comma-separated frontend origins |
| `WHATSAPP_CLOUD_API_TOKEN` | Meta WhatsApp token (optional) |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta phone number ID (optional) |
| `GEMINI_API_KEY` | Google AI Studio key (optional) |
| `ENVIRONMENT` | `production` |

> Nixpacks auto-detects `requirements.txt`; the start command lives in `railway.toml`.

---

## 🔐 Security Notes

- `SECRET_KEY` and `SUPER_ADMIN_KEY` **must** be overridden in production via env vars.
- WhatsApp runs in **simulated mode** until `WHATSAPP_CLOUD_API_TOKEN` is set.
- Auto column migrations in `main.py` are idempotent & dialect-aware (SQLite + PostgreSQL).

---

## 🧹 Dev-Only Scripts

⚠️ `backend/reset_db.py` and `backend/clear_data.py` **wipe all data**. Never run them in production.