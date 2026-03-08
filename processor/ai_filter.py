"""AI 过滤，两步处理（Kimi API）"""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from models import DemandItem, RawItem
from openai import OpenAI

from config import AI_MIN_SCORE, AI_STEP2_DELAY, MOONSHOT_API_KEY

STEP1_PROMPT = """You are a product researcher. Does this text contain a genuine signal that someone wishes a tool or product existed or worked better?

Signals: 'I wish there was', 'why is there no', describing manual workarounds, complaining about missing features.

Text: {text}

Reply ONLY with 'true' or 'false'."""

STEP2_PROMPT = """You are a startup idea evaluator. Analyze this user need and return JSON only. No markdown, no explanation.

Text: {text}

Return exactly:
{{
  "demand_summary": "一句话需求，中文，≤20字",
  "target_user": "who needs this in English",
  "commercial_score": 7,
  "score_reason": "why this score, 1-2 sentences",
  "product_idea": "what product could solve this, 1 sentence"
}}

Score: 1-3=niche, 4-6=possible, 7-8=strong, 9-10=exceptional"""


def _step1_is_demand(client: OpenAI, text: str) -> bool:
    """Step1: 判断是否含真实需求"""
    try:
        prompt = STEP1_PROMPT.format(text=text[:2000])
        resp = client.chat.completions.create(
            model="moonshot-v1-8k",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        content = (resp.choices[0].message.content or "").strip().lower()
        return "true" in content
    except Exception as e:
        print(f"[AI] Step1 调用失败: {e}")
        return False


def _step2_analyze(client: OpenAI, text: str) -> dict | None:
    """Step2: 输出 JSON 结构"""
    try:
        prompt = STEP2_PROMPT.format(text=text[:2000])
        resp = client.chat.completions.create(
            model="moonshot-v1-32k",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        content = (resp.choices[0].message.content or "").strip()
        content = re.sub(r"^```\w*\n?", "", content)
        content = re.sub(r"\n?```\s*$", "", content)
        return json.loads(content)
    except Exception as e:
        print(f"[AI] Step2 解析失败: {e}")
        return None


def filter_demands(items: list[RawItem], executor: ThreadPoolExecutor | None = None) -> list[DemandItem]:
    """Step1 并发，Step2 串行+0.5秒间隔，过滤 score<6"""
    if not MOONSHOT_API_KEY:
        print("[AI] 未配置 MOONSHOT_API_KEY，跳过 AI 过滤")
        return []

    client = OpenAI(api_key=MOONSHOT_API_KEY, base_url="https://api.moonshot.cn/v1")
    item_texts = [(item, f"{item.title}\n{item.body}") for item in items]

    # Step1 并发
    passed_items: list[RawItem] = []
    if executor:
        futures = {
            executor.submit(_step1_is_demand, client, text): (item, text)
            for item, text in item_texts
        }
        for future in as_completed(futures):
            try:
                if future.result():
                    passed_items.append(futures[future][0])
            except Exception as e:
                print(f"[AI] Step1 单条失败: {e}")
    else:
        for item, text in item_texts:
            try:
                if _step1_is_demand(client, text):
                    passed_items.append(item)
            except Exception as e:
                print(f"[AI] Step1 单条失败: {e}")

    # Step2 串行 + 0.5s 间隔
    results: list[DemandItem] = []
    for i, item in enumerate(passed_items):
        if i > 0:
            time.sleep(AI_STEP2_DELAY)
        text = f"{item.title}\n{item.body}"
        data = _step2_analyze(client, text)
        if data is None:
            continue
        score = data.get("commercial_score", 0)
        if isinstance(score, str):
            try:
                score = int(score)
            except ValueError:
                score = 0
        if score < AI_MIN_SCORE:
            continue
        results.append(
            DemandItem(
                raw=item,
                demand_summary=str(data.get("demand_summary", ""))[:20],
                target_user=str(data.get("target_user", "")),
                commercial_score=score,
                score_reason=str(data.get("score_reason", "")),
                product_idea=str(data.get("product_idea", "")),
            )
        )

    results.sort(key=lambda x: x.commercial_score, reverse=True)
    return results
