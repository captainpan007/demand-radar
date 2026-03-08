"""Product Hunt 抓取，GraphQL API"""
import httpx
from models import RawItem

from config import PRODUCTHUNT_API_KEY

PH_ENDPOINT = "https://api.producthunt.com/v2/api/graphql"
MAX_ITEMS = 50


def scrape_producthunt() -> list[RawItem]:
    api_key = PRODUCTHUNT_API_KEY
    print(f"[PH Debug] API Key: {api_key[:10] if api_key else 'EMPTY'}")
    if not PRODUCTHUNT_API_KEY:
        print("[Product Hunt] PRODUCTHUNT_API_KEY not set, skipping")
        return []

    items: list[RawItem] = []

    query = """
{
  posts(first: 50, order: VOTES) {
    edges {
      node {
        id
        name
        tagline
        url
        votesCount
        commentsCount
      }
    }
  }
}
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                PH_ENDPOINT,
                json={"query": query},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"[Product Hunt] request failed: {e}")
        return []

    errors = data.get("errors")
    if errors:
        print(f"[Product Hunt] GraphQL error: {errors}")
        return []

    for edge in data.get("data", {}).get("posts", {}).get("edges", []):
        if len(items) >= MAX_ITEMS:
            break
        node = edge.get("node") or {}
        name = (node.get("name") or "").strip()
        tagline = (node.get("tagline") or "").strip()
        url = node.get("url") or ""
        votes = node.get("votesCount") or 0
        comments_count = node.get("commentsCount") or 0
        if not name and not tagline:
            continue
        title = f"{name}: {tagline}" if tagline else name
        body = (tagline or name)[:1000]
        items.append(
            RawItem(
                source="producthunt",
                title=title[:200],
                body=body,
                url=url,
                score=votes,
                comments=comments_count,
            )
        )
    return items[:MAX_ITEMS]
