"""需求搜集器主入口"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import MOONSHOT_API_KEY
from processor.cleaner import clean, deduplicate
from processor.ai_filter import filter_demands
from reporter.generator import generate_report
from scrapers.g2 import scrape_g2
from scrapers.hn import scrape_hn
from scrapers.reddit import scrape_reddit


async def run():
    if not MOONSHOT_API_KEY:
        print("[启动] 未配置 MOONSHOT_API_KEY，AI 过滤将跳过")
    start = time.perf_counter()
    all_items = []

    # 抓取
    print("=== 阶段 1: 抓取 ===")
    try:
        hn_items = scrape_hn()
        print(f"  [HN] 抓取 {len(hn_items)} 条")
        all_items.extend(hn_items)
    except Exception as e:
        print(f"  [HN] 失败: {e}")

    try:
        reddit_items = scrape_reddit()
        print(f"  [Reddit] 抓取 {len(reddit_items)} 条")
        all_items.extend(reddit_items)
    except Exception as e:
        print(f"  [Reddit] 失败: {e}")

    try:
        g2_items = await scrape_g2()
        print(f"  [G2] 抓取 {len(g2_items)} 条")
        all_items.extend(g2_items)
    except Exception as e:
        print(f"  [G2] 失败: {e}")

    total_raw = len(all_items)
    print(f"  抓取总数: {total_raw}")

    if not all_items:
        print("无数据，退出")
        return

    # 去重
    print("\n=== 阶段 2: 去重 ===")
    items = deduplicate(all_items)
    print(f"  去重后: {len(items)} 条")

    # 清洗
    items = clean(items)
    print(f"  清洗后: {len(items)} 条")

    if not items:
        print("清洗后无数据，退出")
        return

    # AI 过滤
    print("\n=== 阶段 3: AI 过滤 ===")
    with ThreadPoolExecutor(max_workers=5) as executor:
        demands = filter_demands(items, executor)
    print(f"  有效需求: {len(demands)} 条")

    # 生成报告
    print("\n=== 阶段 4: 生成报告 ===")
    output_dir = Path(__file__).parent / "output"
    report_path = generate_report(demands, total_raw=total_raw, output_dir=output_dir)
    print(f"  报告路径: {report_path}")

    elapsed = time.perf_counter() - start
    print(f"\n耗时: {elapsed:.1f} 秒")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
