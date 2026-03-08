"""清洗与去重"""
import hashlib
from models import RawItem


def deduplicate(items: list[RawItem]) -> list[RawItem]:
    """用 title 的 md5 前8位去重"""
    seen: set[str] = set()
    result: list[RawItem] = []
    for item in items:
        h = hashlib.md5(item.title.encode("utf-8")).hexdigest()[:8]
        if h in seen:
            continue
        seen.add(h)
        item.hash = h
        result.append(item)
    return result


def clean(items: list[RawItem]) -> list[RawItem]:
    """过滤空 title，截断 body 到 1000 字，去除换行符"""
    result: list[RawItem] = []
    for item in items:
        if not item.title or not item.title.strip():
            continue
        title = item.title.strip()
        body = (item.body or "").replace("\n", " ").replace("\r", " ")[:1000]
        result.append(
            RawItem(
                source=item.source,
                title=title,
                body=body,
                url=item.url,
                score=item.score,
                comments=item.comments,
                hash=item.hash,
            )
        )
    return result
