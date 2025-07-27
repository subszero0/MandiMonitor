# Product Requirements Document — **@MandiMonitorBot**

---

## 1  Product Overview

| Item                 | Details                                                                                                                                                                                   |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Goal**             | Help price‑conscious Indian shoppers discover and pounce on the lowest online prices without manually scouring every marketplace.                                                         |
| **Primary User Job** | "Tell me the moment a product I want hits my target price / discount **or** when that product is suddenly deeply discounted or bundled with any other lucrative offer."                   |
| **MVP Scope**        | \* Amazon.in only (PA‑API primary source; Playwright scrape fallback)\* English‑only Telegram bot\* Daily digest plus optional 10‑minute real‑time polling\* Up to 5 watch‑lists per user |
| **Non‑Goals (MVP)**  | Multi‑marketplace coverage · AI recommendations · Group‑chat sharing · Payment‑method/coupon intelligence                                                                                 |

---

## 2  Key Features (MVP)

| #      | Feature                      | Summary                                                                                                                          |                                                       |
| ------ | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| **F1** | **/start onboarding**        | Welcome text + single‑paragraph Privacy / Affiliate disclaimer. "Add a watch" button launches flow.                              |                                                       |
| **F2** | **Add‑Watch Flow**           | Free‑text → regex parse → inline buttons capture missing fields.                                                                 |                                                       |
| **F3** | **Immediate Price Snapshot** | Right after a watch is created, bot fetches current best prices & replies with a mini‑carousel so the user sees value instantly. |                                                       |
| **F4** | **Daily Digest**             | One message at user‑chosen time containing up to 5 carousel cards (see §6).                                                      |                                                       |
| **F5** | **Real‑Time Mode**           | \`/realtime on                                                                                                                   | off\` toggles 10‑min polling (muted 23:00–08:00 IST). |
| **F6** | **Stop / List / Delete**     | `/list` enumerates watches with inline ❌ delete. `/stop` clears all jobs.                                                        |                                                       |
| **F7** | **Affiliate Deep Links**     | Every “Buy Now” opens Amazon externally with `?tag=YOURTAG‑21`.                                                                  |                                                       |
| **F8** | **Admin Panel**              | `/admin` (HTTP Basic) → metrics & CSV export.                                                                                    |                                                       |
| **F9** | **Health Endpoint**          | `/health` returns JSON for UptimeRobot.                                                                                          |                                                       |

---

## 3  User Flows

### 3.1  Add Watch (happy path)

1. **User** — "Samsung 27‑inch gaming monitor under 30k"
2. **Bot** parses → missing *min‑discount %* → asks with inline buttons (10 %, 20 %, Skip).
3. **User** taps *10 %*.
4. **Bot** stores the watch, **immediately fetches current prices**, sends a mini‑carousel.
5. Scheduler sets up daily or real‑time jobs as per user default.

### 3.2  Daily Digest

At 09:00 (or user time), digest job ranks matching deals by discount, builds one carousel message (max 5 cards) and sends it.

### 3.3  Real‑Time Toggle

`/realtime on` → reschedules involved watches to every 10 min, auto‑sleep 23:00–08:00 IST. `/realtime off` reverts to daily.

---

## 4  Data Model (SQLModel / SQLite)

```text
User(id INT PK, tg_user_id INT UNIQUE, first_seen TIMESTAMP)
Watch(id INT PK, user_id FK, keywords TEXT,
      brand TEXT NULL, max_price INT NULL, min_discount INT NULL,
      asin TEXT, mode TEXT CHECK('daily','rt'), created TIMESTAMP)
Price(id INT PK, watch_id FK, asin TEXT, price INT,
      fetched_at TIMESTAMP, source TEXT CHECK('paapi','scrape'))
Click(id INT PK, watch_id FK, asin TEXT, clicked_at TIMESTAMP)
```

---

## 5  External Interfaces

| Function                          | I/O                                 | Notes                                               |
| --------------------------------- | ----------------------------------- | --------------------------------------------------- |
| `fetch_price_via_paapi(asin)`     | → `{price, title, image}` or `None` | Uses `python-amazon-paapi`; retries ×3 on throttle. |
| `fetch_price_via_playwright(url)` | → `{price}`                         | Only if PA‑API fails; cached 24 h.                  |
| `/health`                         | GET → `{"status":"ok"}`             | No auth.                                            |
| `/admin`                          | Basic‑auth HTML                     | Shows metrics, CSV export.                          |

---

## 6  Carousel Card Mock‑up (ASCII)

```
┌───────────────────────────┐
│   🔥  ‑42 % |  SAMSUNG     │
│  ───────────────────────  │
│  27" Odyssey G5           │
│  ₹28 999  (now)           │
│  (MRP ₹49 999)            │
│  ☑ Free delivery          │
│                           │
│  [🛒 BUY NOW]              │
└───────────────────────────┘  (card 1/5)
« swipe »   ◀️ ▶️
```

Telegram renders each card as **photo + caption + inline button**; users swipe horizontally.

---

## 7  Tech Stack & Ops

| Layer      | Choice                                                                                                                  |
| ---------- | ----------------------------------------------------------------------------------------------------------------------- |
| Language   | Python 3.12                                                                                                             |
| Core Libs  | `python‑telegram‑bot`, `SQLModel`, `APScheduler`, `python‑amazon‑paapi`, `playwright`, `sentry‑sdk`, `uvicorn`, `flask` |
| Runtime    | Docker Compose on Lightsail (staging & prod)                                                                            |
| Ingress    | Cloudflare Tunnel (free) → HTTPS → bot container                                                                        |
| Storage    | SQLite (`dealbot.db`) backed up nightly to Lightsail Object Storage (free 5 GB / year; \~₹83/mo after)                  |
| CI/CD      | GitHub Actions → Docker image → Amazon ECR → Lightsail deploy script                                                    |
| Monitoring | Sentry (errors), UptimeRobot (health ping), `/admin` metrics                                                            |
| Backup     | Bash cron → copy DB to Object Storage — see [backup‑script gist](LINK_PLACEHOLDER)                                      |

---

## 8  Timeline (4‑Week MVP)

| Week | Deliverable                                                  |
| ---- | ------------------------------------------------------------ |
| 0    | Lightsail box, Cloudflare Tunnel, PA‑API keys, repo skeleton |
| 1    | Price fetcher (PA‑API + scraper) + Prices table              |
| 2    | Telegram bot core: /start, parser, Add‑Watch flow            |
| 3    | Scheduler, Daily Digest carousel, Real‑Time toggle           |
| 4    | Admin panel, metrics, Sentry, backup cron, 5‑friend beta     |

---

## 9  User Stories

*US‑1 (Student)*  — *“As a cash‑strapped engineering student in Delhi, I want to know the moment Uni‑Ball Eye pens drop below ₹25 each so I can bulk‑order for exams without refreshing sites daily.”*

*US‑2 (First‑jobber Gamer)*  — *“As a first‑salary gamer, I want an alert when a Samsung 27‑inch 240 Hz monitor hits a 35 % discount or < ₹30 k, so I can upgrade before weekend LAN parties.”*

*US‑3 (Home Improver)*  — *“As a new homeowner, I need to track 65‑inch smart‑TV deals from Samsung or LG, and get notified if any bank‑card EMI offer brings the price below ₹70 k.”*

---

## 10  Risks & Mitigations

| Risk                  | Mitigation                                                   |
| --------------------- | ------------------------------------------------------------ |
| PA‑API quota exceeded | 24 h cache + scrape fallback; per‑watch force‑refresh guard. |
| Scraping blocked      | Rotate user‑agent; keep fallback frequency low.              |
| Low affiliate clicks  | Future A/B test digest timing & card design.                 |
| Data loss             | Nightly copy to Object Storage + weekly manual download.     |

---

© 2025 MandiMonitorBot — MIT licensed.

