"""Demand Radar — main entry point"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import DEEPSEEK_API_KEY, MOONSHOT_API_KEY
from processor.cleaner import clean, deduplicate
from processor.ai_filter import filter_demands
from reporter.generator import generate_report
from scrapers.g2 import scrape_g2
from scrapers.hn import scrape_hn
from scrapers.indiehackers import scrape_indiehackers
from scrapers.producthunt import scrape_producthunt
from scrapers.reddit import scrape_reddit


async def run():
    if not MOONSHOT_API_KEY:
        print("[startup] MOONSHOT_API_KEY not set, AI filtering will be skipped")
    if not DEEPSEEK_API_KEY:
        print("[startup] DEEPSEEK_API_KEY not set, AI scoring will be skipped")
    start = time.perf_counter()
    all_items = []

    # Scraping
    print("=== Stage 1: Scraping ===")
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
        print("No data, exiting")
        return

    # Deduplication
    print("\n=== Stage 2: Deduplication ===")
    items = deduplicate(all_items)
    print(f"  after dedup: {len(items)} items")

    # Cleaning
    items = clean(items)
    print(f"  after clean: {len(items)} items")

    if not items:
        print("No data after cleaning, exiting")
        return

    # AI filtering
    print("\n=== Stage 3: AI Filtering ===")
    with ThreadPoolExecutor(max_workers=5) as executor:
        demands = filter_demands(items, executor)
    print(f"  qualified demands: {len(demands)}")

    # Report generation
    print("\n=== Stage 4: Report Generation ===")
    output_dir = Path(__file__).parent / "output"
    report_path = generate_report(demands, total_raw=total_raw, output_dir=output_dir)
    print(f"  report path: {report_path}")

    elapsed = time.perf_counter() - start
    print(f"\nelapsed: {elapsed:.1f}s")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
