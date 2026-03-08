"""Indie Hackers 论坛抓取，Playwright 渲染后解析"""
import re

from bs4 import BeautifulSoup
from models import RawItem

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

IH_FORUM_URL = "https://www.indiehackers.com/forum"
MAX_ITEMS = 50


def scrape_indiehackers() -> list[RawItem]:
    if sync_playwright is None:
        print("[IndieHackers] playwright not installed. Run: pip install playwright && playwright install chromium")
        return []

    items: list[RawItem] = []
    seen: set[str] = set()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(IH_FORUM_URL, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1500)
            html = page.content()
            context.close()
            browser.close()
    except Exception as e:
        print(f"[IndieHackers] request failed: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")

    # 帖子链接：/post/xxx 或带标题的 a
    for a in soup.select('a[href*="/post/"]'):
        if len(items) >= MAX_ITEMS:
            break
        href = a.get("href") or ""
        if not href or href in seen:
            continue
        title_text = (a.get_text() or "").strip()
        if not title_text or len(title_text) < 3:
            continue
        if not href.startswith("http"):
            href = "https://www.indiehackers.com" + href.split("?")[0]
        if href in seen:
            continue
        seen.add(href)

        comments = 0
        score = 0
        parent = a.find_parent(["li", "article", "div", "section"])
        if parent:
            for el in parent.select("[class*='comment'], [class*='reply'], [class*='count'], [class*='stat']"):
                num_text = re.sub(r"\D", "", (el.get_text() or ""))
                if num_text:
                    comments = int(num_text)
                    break
            for el in parent.select("[class*='vote'], [class*='score'], [class*='point'], [class*='upvote']"):
                num_text = re.sub(r"\D", "", (el.get_text() or ""))
                if num_text:
                    score = int(num_text)
                    break

        items.append(
            RawItem(
                source="indiehackers",
                title=title_text[:300],
                body="",
                url=href,
                score=score,
                comments=comments,
            )
        )

    if not items:
        for a in soup.find_all("a", href=re.compile(r"/post/|/topic/")):
            if len(items) >= MAX_ITEMS:
                break
            href = (a.get("href") or "").split("?")[0]
            if not href or href in seen:
                continue
            title_text = (a.get_text() or "").strip()
            if not title_text or len(title_text) < 3:
                continue
            if not href.startswith("http"):
                href = "https://www.indiehackers.com" + href
            seen.add(href)
            items.append(
                RawItem(
                    source="indiehackers",
                    title=title_text[:300],
                    body="",
                    url=href,
                    score=0,
                    comments=0,
                )
            )

    return items[:MAX_ITEMS]
