from scrapers.producthunt import scrape_producthunt
from scrapers.indiehackers import scrape_indiehackers

print("=== 测试 Product Hunt ===")
ph_items = scrape_producthunt()
print(f"抓取结果: {len(ph_items)} 条")
if ph_items:
    print(f"第一条: {ph_items[0].title[:50]}")

print("\n=== 测试 IndieHackers ===")
ih_items = scrape_indiehackers()
print(f"抓取结果: {len(ih_items)} 条")
if ih_items:
    print(f"第一条: {ih_items[0].title[:50]}")
