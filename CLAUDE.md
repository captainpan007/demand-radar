# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Demand Radar** (需求雷达) — daily scraper that collects demand signals from developer/indie communities, scores them with AI, and generates an English HTML report for indie developers to find validated product ideas.

**Goal**: scrape HN / Product Hunt / IndieHackers daily → DeepSeek AI scoring → filtered HTML report

**Stack**: Python · DeepSeek API (OpenAI-compatible) · Playwright · Jinja2

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium  # Required for IndieHackers scraper

# Run full pipeline
python main.py
# Output: output/demand-radar-YYYY-MM-DD.html

# Test individual scrapers
python test_scrapers.py
```

## Environment Variables

```bash
# Required
export DEEPSEEK_API_KEY="..."         # AI scoring via DeepSeek-V3

# Optional data sources
export PRODUCTHUNT_API_KEY="..."      # Product Hunt GraphQL API

# Proxy (set before running if behind a proxy)
export HTTPS_PROXY="http://127.0.0.1:7890"
export HTTP_PROXY="http://127.0.0.1:7890"

# Not yet active
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export REDDIT_UA="demand-radar/1.0"
```

## Data Sources

| Source | Status | Auth |
|---|---|---|
| Hacker News | ✅ Active | Free (Algolia API) |
| Product Hunt | ✅ Active | `PRODUCTHUNT_API_KEY` |
| IndieHackers | ✅ Active | Playwright (no auth) |
| Reddit | ⏳ Pending | PRAW (`REDDIT_CLIENT_ID/SECRET`) |
| G2 Reviews | ⏳ Pending | Playwright (no auth) |

## Architecture

**Pipeline** (orchestrated in `main.py`):

1. **Scraping** — `scrapers/` — sequential async:
   - `hn.py`: Algolia search API, terms in `HN_SEARCH_TERMS` (config)
   - `producthunt.py`: GraphQL API, top 50 by votes
   - `indiehackers.py`: Playwright headless, forum page, up to 50 posts
   - `reddit.py`: PRAW — r/SomebodyMakeThis, r/entrepreneur *(inactive, no key)*
   - `g2.py`: Playwright headless, low-star reviews *(inactive)*

2. **Cleaning** — `processor/cleaner.py` — MD5 dedup on title, truncate body to 1000 chars

3. **AI Filtering** — `processor/ai_filter.py` — DeepSeek-V3, concurrent (5 workers):
   - Hard veto: no payment precedent / needs team / big tech covers it / physical goods
   - 4-dim score: `pain_level` (0–3) + `payment_signal` (0–3) + `executability` (0–2) + `reach` (0–2)
   - Drop if total < `AI_MIN_SCORE` (default 6)
   - Each passing item gets: `build_days`, `tool_plan`, `cost_estimate`, `biggest_risk`

4. **Reporting** — `reporter/generator.py` + `reporter/template.html`:
   - Jinja2-rendered HTML, dark minimal UI
   - Interactive cards (expand/collapse), localStorage favorites
   - EN/ZH language toggle (JS, no re-render needed)

## Data Models (`models.py`)

- `RawItem`: source, title, body, url, score, comments, hash
- `DemandItem`: wraps RawItem + AI fields (demand_summary, target_user, commercial_score, score_detail, product_idea, build_days, tool_plan, cost_estimate, biggest_risk)

## Key Config (`config.py`)

- `HN_SEARCH_TERMS`: Algolia queries — edit to change signal types
- `AI_MIN_SCORE`: threshold (default 6); raise for higher quality
- `AI_TOOLS`: 8-tool library referenced in AI execution plans
- DeepSeek endpoint: `https://api.deepseek.com`, model `deepseek-chat`
