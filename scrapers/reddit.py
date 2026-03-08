"""Reddit 抓取，使用 praw"""
from models import RawItem

from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_UA


def scrape_reddit() -> list[RawItem]:
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        print("[Reddit] REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set, skipping")
        return []

    try:
        import praw
    except ImportError:
        print("[Reddit] praw not installed, skipping")
        return []

    items: list[RawItem] = []
    seen_ids: set[str] = set()

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_UA,
        )
    except Exception as e:
        print(f"[Reddit] init failed: {e}")
        return []

    # r/SomebodyMakeThis, hot, 30
    try:
        for post in reddit.subreddit("SomebodyMakeThis").hot(limit=30):
            if post.id in seen_ids:
                continue
            seen_ids.add(post.id)
            items.append(
                RawItem(
                    source="reddit",
                    title=post.title or "",
                    body=post.selftext or "",
                    url=f"https://reddit.com{post.permalink}",
                    score=post.score or 0,
                    comments=post.num_comments or 0,
                )
            )
    except Exception as e:
        print(f"[Reddit] r/SomebodyMakeThis scrape failed: {e}")

    # r/entrepreneur 搜索 "I wish there was", 20
    try:
        for post in reddit.subreddit("entrepreneur").search(
            "I wish there was", sort="relevance", limit=20
        ):
            if post.id in seen_ids:
                continue
            seen_ids.add(post.id)
            items.append(
                RawItem(
                    source="reddit",
                    title=post.title or "",
                    body=post.selftext or "",
                    url=f"https://reddit.com{post.permalink}",
                    score=post.score or 0,
                    comments=post.num_comments or 0,
                )
            )
    except Exception as e:
        print(f"[Reddit] r/entrepreneur search failed: {e}")

    # r/smallbusiness 搜索 "wish there was a tool", 15
    try:
        for post in reddit.subreddit("smallbusiness").search(
            "wish there was a tool", sort="relevance", limit=15
        ):
            if post.id in seen_ids:
                continue
            seen_ids.add(post.id)
            items.append(
                RawItem(
                    source="reddit",
                    title=post.title or "",
                    body=post.selftext or "",
                    url=f"https://reddit.com{post.permalink}",
                    score=post.score or 0,
                    comments=post.num_comments or 0,
                )
            )
    except Exception as e:
        print(f"[Reddit] r/smallbusiness search failed: {e}")

    # r/freelance 搜索 "automate", 15
    try:
        for post in reddit.subreddit("freelance").search(
            "automate", sort="relevance", limit=15
        ):
            if post.id in seen_ids:
                continue
            seen_ids.add(post.id)
            items.append(
                RawItem(
                    source="reddit",
                    title=post.title or "",
                    body=post.selftext or "",
                    url=f"https://reddit.com{post.permalink}",
                    score=post.score or 0,
                    comments=post.num_comments or 0,
                )
            )
    except Exception as e:
        print(f"[Reddit] r/freelance search failed: {e}")

    return items
