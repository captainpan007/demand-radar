"""HN 抓取，使用 Algolia API"""
import httpx
from models import RawItem

from config import HN_API_URL, HN_SEARCH_TERMS


def scrape_hn() -> list[RawItem]:
    items: list[RawItem] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=30) as client:
        for query in HN_SEARCH_TERMS:
            try:
                resp = client.get(
                    HN_API_URL,
                    params={
                        "query": query,
                        "tags": "ask_hn",
                        "numericFilters": "points>3",
                        "hitsPerPage": 20,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[HN] search '{query}' failed: {e}")
                continue

            for hit in data.get("hits", []):
                oid = hit.get("objectID", "")
                if oid in seen_ids:
                    continue
                seen_ids.add(oid)

                title = hit.get("title", "").strip()
                body = hit.get("story_text", "") or ""
                if isinstance(body, str):
                    body = body.replace("&#x27;", "'").replace("&quot;", '"')
                else:
                    body = str(body)

                items.append(
                    RawItem(
                        source="hn",
                        title=title,
                        body=body,
                        url=f"https://news.ycombinator.com/item?id={oid}",
                        score=hit.get("points", 0),
                        comments=hit.get("num_comments", 0),
                    )
                )

    return items
