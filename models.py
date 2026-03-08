from dataclasses import dataclass


@dataclass
class RawItem:
    source: str  # 'hn' | 'reddit' | 'g2'
    title: str
    body: str
    url: str
    score: int
    comments: int
    hash: str = ""


@dataclass
class DemandItem:
    raw: RawItem
    demand_summary: str
    target_user: str
    commercial_score: int
    score_reason: str
    product_idea: str
