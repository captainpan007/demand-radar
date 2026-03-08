"""G2 抓取，使用 playwright 异步 API"""
import random
from models import RawItem

from config import G2_CATEGORIES, G2_DELAY_MIN, G2_DELAY_MAX


async def scrape_g2() -> list[RawItem]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[G2] playwright not installed, skipping. Run: pip install playwright && playwright install chromium")
        return []

    items: list[RawItem] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for cat in G2_CATEGORIES:
                try:
                    page = await browser.new_page()
                    page.set_default_timeout(30000)
                    url = f"https://www.g2.com/categories/{cat}"
                    await page.goto(url, wait_until="domcontentloaded")
                    delay = random.uniform(G2_DELAY_MIN, G2_DELAY_MAX)
                    await page.wait_for_timeout(int(delay * 1000))

                    # 抓取页面上的评价元素，优先 1-3 星
                    review_els = await page.query_selector_all(
                        '[data-testid="review"], .review-card, [class*="Review"]'
                    )
                    if not review_els:
                        review_els = await page.query_selector_all(
                            '[class*="review"]'
                        )

                    for el in review_els[:15]:
                        try:
                            title_el = await el.query_selector(
                                "h3, h4, [class*='title'], [class*='headline']"
                            )
                            body_el = await el.query_selector(
                                "p, [class*='body'], [class*='content']"
                            )
                            rating_el = await el.query_selector(
                                "[class*='star'], [class*='rating'], [aria-label*='star']"
                            )
                            title = await title_el.inner_text() if title_el else ""
                            body = await body_el.inner_text() if body_el else ""
                            rating_text = ""
                            if rating_el:
                                rating_text = (
                                    await rating_el.get_attribute("aria-label")
                                    or await rating_el.inner_text()
                                    or ""
                                )
                            stars = 0
                            if rating_text:
                                if "1" in rating_text or "one" in rating_text.lower():
                                    stars = 1
                                elif "2" in rating_text or "two" in rating_text.lower():
                                    stars = 2
                                elif "3" in rating_text or "three" in rating_text.lower():
                                    stars = 3
                            if stars == 0 and (body or title):
                                stars = 3
                            if 0 < stars <= 3 and (title or body):
                                text = f"{title}\n{body}".strip()
                                if len(text) > 20:
                                    items.append(
                                        RawItem(
                                            source="g2",
                                            title=(title[:200] if title else text[:100]) or "G2 Review",
                                            body=body[:1000] if body else text[:1000],
                                            url=page.url,
                                            score=0,
                                            comments=0,
                                        )
                                    )
                        except Exception:
                            pass
                    await page.close()
                except Exception as e:
                    print(f"[G2] category {cat} failed: {e}")
        finally:
            await browser.close()

    return items
