"""Reusable scraping pipeline that writes results to SQLite via storage.py."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from config import DEEPSEEK_API_KEY
from processor.cleaner import clean, deduplicate
from processor.ai_filter import filter_demands
from processor.translator import translate_demands
from scrapers.g2 import scrape_g2
from scrapers.hn import scrape_hn
from scrapers.indiehackers import scrape_indiehackers
from scrapers.producthunt import scrape_producthunt
from scrapers.reddit import scrape_reddit
from storage import save_demands


async def run_pipeline(session_factory) -> dict:
    """Run the full scraping pipeline and save results to DB.

    Parameters
    ----------
    session_factory : sqlalchemy.orm.sessionmaker
        A SQLAlchemy session factory (call it to get a session).

    Returns
    -------
    dict with keys: total_raw, after_dedup, qualified, saved, elapsed
    """
    if not DEEPSEEK_API_KEY:
        print("[pipeline] DEEPSEEK_API_KEY not set, AI scoring will be skipped")

    start = time.perf_counter()
    all_items = []

    # --- Stage 1: Scraping ---
    print("=== Pipeline Stage 1: Scraping ===")

    try:
        hn_items = scrape_hn()
        print(f"  [HN] fetched {len(hn_items)} items")
        all_items.extend(hn_items)
    except Exception as e:
        print(f"  [HN] failed: {e}")

    try:
        reddit_items = scrape_reddit()
        print(f"  [Reddit] fetched {len(reddit_items)} items")
        all_items.extend(reddit_items)
    except Exception as e:
        print(f"  [Reddit] failed: {e}")

    try:
        g2_items = await scrape_g2()
        print(f"  [G2] fetched {len(g2_items)} items")
        all_items.extend(g2_items)
    except Exception as e:
        print(f"  [G2] failed: {e}")

    try:
        ph_items = scrape_producthunt()
        print(f"  [Product Hunt] fetched {len(ph_items)} items")
        all_items.extend(ph_items)
    except Exception as e:
        print(f"  [Product Hunt] failed: {e}")

    try:
        ih_items = scrape_indiehackers()
        print(f"  [IndieHackers] fetched {len(ih_items)} items")
        all_items.extend(ih_items)
    except Exception as e:
        print(f"  [IndieHackers] failed: {e}")

    total_raw = len(all_items)
    print(f"  total fetched: {total_raw}")

    if not all_items:
        elapsed = time.perf_counter() - start
        print("No data scraped, pipeline finished early")
        return {
            "total_raw": 0,
            "after_dedup": 0,
            "qualified": 0,
            "saved": 0,
            "elapsed": round(elapsed, 1),
        }

    # --- Stage 2: Deduplication + Cleaning ---
    print("\n=== Pipeline Stage 2: Deduplication ===")
    items = deduplicate(all_items)
    after_dedup = len(items)
    print(f"  after dedup: {after_dedup} items")

    items = clean(items)
    print(f"  after clean: {len(items)} items")

    if not items:
        elapsed = time.perf_counter() - start
        print("No data after cleaning, pipeline finished early")
        return {
            "total_raw": total_raw,
            "after_dedup": after_dedup,
            "qualified": 0,
            "saved": 0,
            "elapsed": round(elapsed, 1),
        }

    # --- Stage 3: AI Filtering ---
    print("\n=== Pipeline Stage 3: AI Filtering ===")
    with ThreadPoolExecutor(max_workers=5) as executor:
        demands = filter_demands(items, executor)
    qualified = len(demands)
    print(f"  qualified demands: {qualified}")

    # --- Stage 3.5: Translate to Chinese ---
    print("\n=== Pipeline Stage 3.5: Translate to Chinese ===")
    with ThreadPoolExecutor(max_workers=5) as executor:
        translated = translate_demands(demands, executor)
    print(f"  translated: {translated}/{qualified}")

    # --- Stage 4: Save to DB ---
    print("\n=== Pipeline Stage 4: Save to DB ===")
    db = session_factory()
    try:
        saved = save_demands(db, demands, report_date=date.today())
        print(f"  saved {saved} new demands to DB")
    finally:
        db.close()

    elapsed = time.perf_counter() - start
    print(f"\nPipeline elapsed: {elapsed:.1f}s")

    return {
        "total_raw": total_raw,
        "after_dedup": after_dedup,
        "qualified": qualified,
        "saved": saved,
        "elapsed": round(elapsed, 1),
    }


def run_pipeline_sync(session_factory) -> dict:
    """Synchronous wrapper for run_pipeline, suitable for APScheduler."""
    return asyncio.run(run_pipeline(session_factory))
