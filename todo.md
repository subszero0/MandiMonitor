# TODO — Sprint‑level Task Breakdown for **@MandiMonitorBot**

> **Guiding principle**  Small, atomic tasks → fewer surprises when Cursor generates code.  Each sub‑task should compile / run in isolation before moving on.

---

## 📁 Phase 0 — Repo & Environment (Day 1–2)

- **T0‑1 Create GitHub repo**  
  - Initialise with MIT licence, `README.md`, `.gitignore (Python + Docker)`
- **T0‑2 Local Python toolchain**  
  - Install Python 3.12 via pyenv  
  - `pipx install poetry` (or virtualenv)  
  - `poetry init` → add core libs as empty deps for now
- **T0‑3 Docker skeleton**  
  - Write minimal `Dockerfile` (Python slim, copy src, `pip install -r requirements.txt`)  
  - Draft `docker‑compose.yml` with **bot**, **nginx (blank)** services
- **T0‑4 .env scaffolding**  
  - Create `.env.example` with placeholders for `TELEGRAM_TOKEN`, `PAAPI_KEY`, etc.
- **T0‑5 First push & CI stub**  
  - Enable GitHub Actions → add empty workflow (`on: push` log “CI up”).

---

## 🔑 Phase 1 — Credentials & Health Check (Day 3)

- **T1‑1 Get PA‑API credentials**  
  - Sign up Amazon Associates → record `ACCESS_KEY`, `SECRET_KEY`, `TAG`
- **T1‑2 Generate BotFather token**  
  - Set bot name = *MandiMonitorBot*; store token in `.env`
- **T1‑3 Hello‑world bot**  
  - `python‑telegram‑bot` echo `/start` → “Bot alive”  
  - Add `/health` Flask route returning `{"status":"ok"}`
- **T1‑4 Cloudflare Tunnel smoke test**  
  - Install `cloudflared` locally; run a transient tunnel → verify HTTPS URL proxies bot.

---

## 🏗️ Phase 2 — Price Fetch Sub‑system (Day 4‑5)

- **T2‑1 Install libs**  
  - `python‑amazon‑paapi`, `playwright`, `sqlmodel`
- **T2‑2 Write `paapi_wrapper.py`**  
  - Function `get_item(asin) -> {price,title,image}`  
  - Log quota headers; raise custom error on 503
- **T2‑3 Playwright scraper POC**  
  - Headless Chromium → open sample Amazon page → CSS select price  
  - Return `price` as int; save HTML locally for debugging
- **T2‑4 24‑h cache layer**  
  - Simple SQLite table `cache(asin, price, fetched_at)`  
  - `get_price(asin)` → check cache first
- **T2‑5 Unit tests**  
  - Pytest: mock PA‑API response; assert numeric output.

---

## 📝 Phase 3 — Data Models & Migration (Day 6)

- **T3‑1 Define SQLModel classes** (`User`, `Watch`, `Price`, `Click`)
- **T3‑2 Init SQLite**  
  - `engine = create_engine('sqlite:///dealbot.db', echo=True)`  
  - `SQLModel.metadata.create_all(engine)`
- **T3‑3 Alembic optional**  
  - Decide if schema evolution needed now; skip if time‑boxed.

---

## 💬 Phase 4 — Watch Creation Flow (Day 7‑9)

- **T4‑1 Regex patterns file**  
  - Patterns for brand, size (inch), "under <price>", "% discount"
- **T4‑2 Inline button helpers**  
  - `build_brand_buttons(list)`; `build_discount_buttons()`
- **T4‑3 `/watch` handler**  
  - Parse free text → missing fields? → send buttons  
  - On completion → insert into `Watch` + invoke immediate price fetch (Phase 2 funcs)
- **T4‑4 Immediate mini‑carousel**  
  - Compose single card; send photo+caption+Buy Now button
- **T4‑5 Error paths**  
  - If ASIN lookup fails → politely ask for clearer phrase

---

## ⏰ Phase 5 — Schedulers (Day 10‑12)

- **T5‑1 Add APScheduler**  
  - `BackgroundScheduler()` singleton
- **T5‑2 Daily job creator**  
  - For each watch where `mode='daily'`, schedule at user‑selected time
- **T5‑3 Real‑time job creator**  
  - 10‑min polling; mute via scheduler pause between 23:00–08:00 IST
- **T5‑4 Digest builder**  
  - Query price history → pick best 5 by discount → build 5‑card carousel

---

## 🔗 Phase 6 — Affiliate Deep Links (Day 13)

- **T6‑1 Helper `build_affiliate_url(asin)`**  
  - Append `?tag={{YOURTAG}}`  
  - Add `&linkCode=ogi&th=1&psc=1` for reliability
- **T6‑2 Track click‑outs**  
  - Inline button callback logs `Click` row before redirecting

---

## 📊 Phase 7 — Admin & Metrics (Day 14‑15)

- **T7‑1 Flask `/admin` route**  
  - Basic Auth via `ADMIN_USER/PASS` env vars
- **T7‑2 Metrics query**  
  - SQL count for explorers (`User`), watch creators, live watches, click‑outs, scraper fallbacks
- **T7‑3 CSV download**  
  - Stream `Price` table as CSV

---

## 🔒 Phase 8 — Monitoring & Back‑ups (Day 15)

- **T8‑1 Sentry setup** (`sentry_sdk.init(dsn, traces_sample_rate=1.0)`)  
- **T8‑2 /health integration**  
  - Register URL with UptimeRobot free plan
- **T8‑3 Backup cron script**  
  - Write shell script; `crontab -e` → `0 2 * * * /home/ubuntu/backup_db.sh`

---

## 📦 Phase 9 — Docker & CI/CD (Day 16‑18)

- **T9‑1 Dockerfile finalise**  
  - Multi‑stage build (build then slim run)  
  - Entrypoint `uvicorn bot.main:app --port 8000`
- **T9‑2 compose file**  
  - Define services: bot, cloudflared (tunnel), cron container (optional)
- **T9‑3 GitHub Actions workflow**  
  - Trigger on push → build image → push to ECR → SSH to Lightsail → `docker compose pull && up -d`

---

## 🧪 Phase 10 — Beta Test (Day 19‑22)

- **T10‑1 Add 5 friends** to private Telegram group
- **T10‑2 Collect feedback**  
  - Note parse failures, spam complaints, price accuracy issues
- **T10‑3 Patch & iterate**  
  - Fix high‑priority bugs; redeploy via CI

---

## 🚀 Phase 11 — Public Soft‑Launch (Day 23‑28)

- **T11‑1 Write launch blurb** (Telegram, LinkedIn)  
- **T11‑2 Enable Cloudflare custom sub‑domain** (`bot.mandimonitor.com`)
- **T11‑3 Monitor load**  
  - Watch Sentry, `/admin`, UptimeRobot for week 1.

---

### ✨ Stretch / Nice‑to‑haves (post‑MVP)

- Multi‑marketplace modules (Flipkart API, Keepa)  
- Postgres migration using SQLModel + Alembic  
- Coupon / bank‑offer enrichment  
- Dark‑mode inline card styling

---

*Last updated: 2025‑07‑27*

