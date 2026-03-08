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

## Current Status (2026-03-08)

- **Active sources**: HN · Product Hunt · IndieHackers
- **Daily output**: ~40 qualified demand signals from ~80 raw items
- **Stage**: local personal tool — run manually via `python main.py`
- **Known issues**: IndieHackers fails inside asyncio loop (Playwright sync/async conflict — pre-existing)

## Next Steps

1. **Private GitHub backup** — version control, protect iteration history
2. **Landing page** — simple page describing the tool, collect early interest emails
3. **Early user validation** — share reports with 5–10 indie developers, gather feedback
4. **Automate daily run** — cron job or GitHub Actions scheduled workflow
5. **Reddit + G2 activation** — add PRAW credentials, fix G2 Playwright selectors
