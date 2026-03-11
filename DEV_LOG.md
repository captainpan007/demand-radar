# DEV_LOG.md — Demand Radar

## Milestones

### v0.1 — HN Scraper + DeepSeek Baseline
- Hacker News scraping via Algolia free API
- DeepSeek-V3 single-call scoring pipeline
- Basic HTML report output

### v0.2 — 4-Dimension Scoring System
- Replaced flat score with 4-dimensional model:
  - Pain Level (0–3) · Pay Signal (0–3) · Buildability (0–2) · Reach (0–2)
- Added hard veto rules (no payment precedent / needs team / big tech / physical goods)
- Items below score 6 filtered out
- Each qualified item now includes an AI-generated execution plan (build_days, tool_plan, cost_estimate, biggest_risk)

### v0.3 — UI Iteration
- Initial cyberpunk neon aesthetic
- Revised to clean dark minimal style (Inter font, subtle accent colors, score-colored left border)
- Interactive expand/collapse cards, localStorage favorites, filter-by-saved

### v0.4 — Multi-source + Internationalization
- **Product Hunt**: GraphQL API integration, top 50 posts by votes
- **IndieHackers**: Playwright headless scraper, forum page, up to 50 posts
- **English internationalization**: all UI labels, AI prompt rewritten in English (AI outputs English content)
- **EN/ZH language toggle**: JS-only switch, no re-render required; covers all UI labels while keeping AI-generated content unchanged

---

### v0.5 — Web Product + Railway Deployment (2026-03-10)
- **FastAPI web app** with Google OAuth login
- **3-tier access**: visitor (3 items), free (5 items), pro (unlimited)
- **Lemon Squeezy** subscription at $9/mo
- **Pro features**: historical reports with date picker, keyword search
- **Railway deployment** with persistent SQLite volume
- **APScheduler** daily cron at 06:00 UTC

---

## Railway Environment Variables

**Pan must add these manually in Railway dashboard → Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | Yes | AI scoring API key |
| `PRODUCTHUNT_API_KEY` | Yes | Product Hunt GraphQL API key |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `SECRET_KEY` | Yes | Session encryption key (random string) |
| `BASE_URL` | Yes | `https://demand-radar-production.up.railway.app` |
| `LEMON_SQUEEZY_CHECKOUT_URL` | Yes | Checkout URL from Lemon Squeezy product page |
| `LEMON_SQUEEZY_SIGNING_SECRET` | Yes | Webhook signing secret from Lemon Squeezy settings |

**Lemon Squeezy Webhook URL** (set in Lemon Squeezy dashboard):
`https://demand-radar-production.up.railway.app/webhook/lemon`

Events to subscribe: `subscription_created`, `subscription_updated`, `subscription_expired`

---

### v0.5.1 — PostgreSQL Migration + UI Redesign (2026-03-10)
- **PostgreSQL migration**: SQLite wiped on every Railway redeploy → switched to PostgreSQL via `DATABASE_URL`
  - `database.py`: auto-detect PostgreSQL vs SQLite, fix `postgres://` → `postgresql://`
  - `storage.py`: ILIKE search for PostgreSQL, FTS5 only for SQLite
  - Removed `[[mounts]]` volume from `railway.toml`
  - Added `psycopg2-binary` to requirements
- **UI redesign**: plain list → card grid layout (Exploding Topics/Treendly style)
  - Source badges (HN orange, PH red, IH blue), trend indicators, score rings, filter bar
  - Dark premium aesthetic with Inter font
- **Chinese translations**: added `_zh` fields to `DemandItem` and `Demand` model
- **Pricing page** and **search page** redesigned to match new style

### v0.5.2 — Title Truncation Bug Fix (2026-03-11)
- **Root cause**: `ai_filter.py:153` had `[:50]` hard truncation on `demand_summary` — all prior CSS/JS fixes were treating symptoms
- **Fix**: removed `[:50]`, data now stores full-length summaries
- Added `truncate_words()` Jinja2 filter for display-layer word-boundary truncation (90 chars max)
- Removed all client-side JS truncation code
- Added `/admin/rerun-today` endpoint to clear and re-populate today's data with full summaries
- **Debugging approach**: used `superpowers:systematic-debugging` skill — Phase 1 evidence gathering on production HTML revealed data was already truncated at storage layer

### v0.5.3 — Security Audit & Hardening (2026-03-11)
- **Audit tool**: used `everything-claude-code:security-review` skill for full checklist review
- **CRITICAL fixes**:
  - `webhook.py`: signature verification now **fails closed** (rejects when signing secret not set, was accepting all)
  - `app.py`: admin endpoints `/admin/run-pipeline` and `/admin/rerun-today` now require `ADMIN_TOKEN` Bearer auth
- **HIGH fixes**:
  - `auth.py`: removed debug logging of Google Client ID (was printing first 20 chars to stdout)
  - `auth.py`: session cookie now sets `Secure` flag in production (when `BASE_URL` is not localhost)
- **MEDIUM fixes**:
  - `storage.py`: ILIKE search now escapes `%`, `_`, `\` wildcards in user input
- **Verified safe**: Jinja2 auto-escaping (no `|safe`), SQLAlchemy parameterized queries, `secrets.token_urlsafe(32)` for sessions, `.env` in `.gitignore` + `.dockerignore`
- **Remaining recommendations**: add rate limiting (`slowapi`), purge expired sessions, migrate `datetime.utcnow()` → `datetime.now(timezone.utc)`

---

## Railway Environment Variables

**Updated — must also set:**

| Variable | Required | Description |
|----------|----------|-------------|
| `ADMIN_TOKEN` | Yes | Random token for admin API access (generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`) |

---

## Current Status (2026-03-11)

- **Active sources**: HN · Product Hunt · IndieHackers
- **Daily output**: ~44 qualified demand signals from ~99 raw items
- **Database**: PostgreSQL on Railway (migrated from SQLite)
- **Stage**: deployed on Railway, live at https://demand-radar-production.up.railway.app
- **Security**: audited and hardened (v0.5.3), admin endpoints protected, webhook signature fail-closed
- **Known issues**: IndieHackers fails inside asyncio loop (Playwright sync/async conflict — pre-existing)

## Next Steps

1. **Set `ADMIN_TOKEN`** on Railway dashboard — required for admin API access
2. **Add rate limiting** — `slowapi` package for `/auth/google`, `/search`, webhook
3. **Session cleanup** — cron to purge expired sessions from DB
4. **Landing page** — simple page describing the tool, collect early interest emails
5. **Early user validation** — share reports with 5–10 indie developers, gather feedback
6. **Reddit + G2 activation** — add PRAW credentials, fix G2 Playwright selectors
