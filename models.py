from dataclasses import dataclass, field


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
    build_days: str = ""
    tool_plan: list = field(default_factory=list)  # [{"tool": "工具名", "role": "负责什么"}, ...]
    score_detail: dict = field(default_factory=dict)  # pain_level, payment_signal, executability, reach
    cost_estimate: str = ""
    biggest_risk: str = ""
    # Chinese translations (populated from DB, not from AI filter)
    demand_summary_zh: str = ""
    target_user_zh: str = ""
    product_idea_zh: str = ""
    score_reason_zh: str = ""
    build_days_zh: str = ""
    tool_plan_zh: list = field(default_factory=list)
    cost_estimate_zh: str = ""
    biggest_risk_zh: str = ""
