"""Batch translate DemandItem English fields to Chinese using DeepSeek."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import DemandItem
from processor.ai_filter import deepseek_client

TRANSLATE_PROMPT = """Translate the following JSON fields from English to Chinese.
Keep all JSON keys unchanged. Only translate the string values.
For the tool_plan array, translate each "role" value but keep "tool" names in English.

Input JSON:
{json_input}

Output only the translated JSON. No markdown wrapper. No explanation."""


def _translate_one(item: DemandItem, total: int, done_counter: list, lock: threading.Lock) -> bool:
    """Translate one DemandItem's fields to Chinese. Returns True on success."""
    if deepseek_client is None:
        return False

    fields = {
        "demand_summary": item.demand_summary,
        "target_user": item.target_user,
        "product_idea": item.product_idea,
        "score_reason": item.score_reason,
        "build_days": item.build_days,
        "cost_estimate": item.cost_estimate,
        "biggest_risk": item.biggest_risk,
        "tool_plan": item.tool_plan,
    }

    try:
        prompt = TRANSLATE_PROMPT.format(json_input=json.dumps(fields, ensure_ascii=False))
        resp = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = (resp.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        data = json.loads(raw)

        item.demand_summary_zh = str(data.get("demand_summary", ""))
        item.target_user_zh = str(data.get("target_user", ""))
        item.product_idea_zh = str(data.get("product_idea", ""))
        item.score_reason_zh = str(data.get("score_reason", ""))
        item.build_days_zh = str(data.get("build_days", ""))
        item.cost_estimate_zh = str(data.get("cost_estimate", ""))
        item.biggest_risk_zh = str(data.get("biggest_risk", ""))

        tp = data.get("tool_plan")
        if isinstance(tp, list):
            item.tool_plan_zh = [x for x in tp if isinstance(x, dict) and x.get("tool") and x.get("role")]
        else:
            item.tool_plan_zh = []

        with lock:
            done_counter[0] += 1
            print(f"[Translate] progress {done_counter[0]}/{total}")
        return True

    except Exception as e:
        print(f"[Translate] item failed: {type(e).__name__}: {str(e)}")
        with lock:
            done_counter[0] += 1
            print(f"[Translate] progress {done_counter[0]}/{total}")
        return False


def translate_demands(items: list[DemandItem], executor: ThreadPoolExecutor | None = None) -> int:
    """Translate all DemandItems to Chinese concurrently. Returns count of successful translations."""
    if deepseek_client is None:
        print("[Translate] DeepSeek client not available, skipping translation")
        return 0

    total = len(items)
    if total == 0:
        return 0

    done_counter: list = [0]
    lock = threading.Lock()
    pool = executor or ThreadPoolExecutor(max_workers=5)
    own_executor = executor is None

    success = 0
    try:
        futures = {pool.submit(_translate_one, item, total, done_counter, lock): item for item in items}
        for future in as_completed(futures):
            try:
                if future.result():
                    success += 1
            except Exception as e:
                print(f"[Translate] error: {type(e).__name__}: {str(e)}")
    finally:
        if own_executor:
            pool.shutdown(wait=True)

    print(f"[Translate] {success}/{total} items translated to Chinese")
    return success
