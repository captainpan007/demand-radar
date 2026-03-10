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

## Current Status (2026-03-10)

- **Active sources**: HN · Product Hunt · IndieHackers
- **Daily output**: ~44 qualified demand signals from ~99 raw items
- **Stage**: deployed on Railway, live at https://demand-radar-production.up.railway.app
- **Known issues**: IndieHackers fails inside asyncio loop (Playwright sync/async conflict — pre-existing)

## Next Steps

1. **Private GitHub backup** — version control, protect iteration history
2. **Landing page** — simple page describing the tool, collect early interest emails
3. **Early user validation** — share reports with 5–10 indie developers, gather feedback
4. **Automate daily run** — cron job or GitHub Actions scheduled workflow
5. **Reddit + G2 activation** — add PRAW credentials, fix G2 Playwright selectors
