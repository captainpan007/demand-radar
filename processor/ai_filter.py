"""AI filtering — single-call + concurrent (DeepSeek)"""
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
from models import DemandItem, RawItem
from openai import OpenAI

from config import AI_MIN_SCORE, AI_TOOLS, DEEPSEEK_API_KEY

_dk = os.environ.get("DEEPSEEK_API_KEY")
if _dk:
    deepseek_client = OpenAI(
        api_key=_dk,
        base_url="https://api.deepseek.com",
        http_client=httpx.Client(trust_env=False),  # bypass system proxy, connect directly
    )
else:
    deepseek_client = None


def _tools_str() -> str:
    return "\n".join(f"- {t['name']}: {t['specialty']} ({t['best_for']})" for t in AI_TOOLS)


SCORE_PROMPT = """You are an analyst who helps indie developers identify and execute product opportunities.

[Step 1: Hard veto checks (instant elimination — return {{"commercial_score": 0}})]
If ANY of the following apply, reject immediately without scoring:
- No payment precedent: no evidence anyone has ever paid for a similar solution, no paid competitors exist
- MVP requires more than one person (e.g., needs a dedicated designer + backend + frontend split)
- A mature free product from a big tech company already covers this (Google, Apple, Microsoft built-in features)
- Physical goods / offline / supply chain / hardware / requires government licenses

[Step 2: Four-dimension scoring (only if the item passes Step 1)]

Dimension 1: Pain Level (0–3) — the most important dimension
3: Hair-on-fire — strong emotion words in the description (frustrated, hate, waste hours, killing me, desperate), or repeated multiple times
2: Clearly painful — user knows it's a problem but tone is calm
1: Mild inconvenience — nice-to-have, user "wishes it existed" but doesn't urgently need it
0: Pure feature request, no emotional signal

Dimension 2: Payment Signal (0–3)
3: Explicit evidence — user directly says they'd pay, or multiple paid competitors already exist
2: Indirect evidence — paid competitors exist but are immature, or the use case is professional/commercial (B2B pays more readily)
1: Latent possibility — consumer context, no direct payment signal
0: Pure personal preference, or strong expectation of free

Dimension 3: Solo Buildability (0–2)
2: One developer can ship MVP within 2 months
1: One developer can build it but needs 3–6 months
0: Technical complexity exceeds one person's scope, or requires large non-technical resources

Dimension 4: Reach Clarity (0–2)
2: Clear acquisition channel (e.g., "r/freelance on Reddit", "HN audience", "Shopify merchants")
1: Target audience exists but acquisition is vague
0: Audience too broad ("everyone") or too niche (no concentration point)

Total = D1 + D2 + D3 + D4 (max 10). Items below 6 are filtered out.

[Scoring reminders]
- D1 and D2 are the core; if they sum to less than 4, the opportunity is almost never worth pursuing
- Be strict — a flat 6 across all dimensions means you're hedging
- Every score must have a concrete reason, not just "good" or "average"

The score_reason field must state: 1. which dimension scored highest and why; 2. which scored lowest and why; 3. whether a hard veto was triggered and which rule.
score_detail must include the exact numeric score for each dimension.

Part 2: Build plan using AI tools

Available tool library:
{tools_str}

Select 2–4 tools from the library that best fit this project and explain what each handles.

Output JSON:
{{
  "commercial_score": <total score>,
  "score_reason": "Highest dimension: ... (reason). Lowest dimension: ... (reason). Hard veto triggered: yes/no (which rule if yes).",
  "score_detail": {{
    "pain_level": 0-3,
    "payment_signal": 0-3,
    "executability": 0-2,
    "reach": 0-2
  }},
  "target_user": "Specific description of the target user",
  "demand_summary": "One-sentence summary of the user's real pain",
  "product_idea": "Concrete form of the minimum viable product",
  "build_days": "X–X days",
  "tool_plan": [
    {{"tool": "Tool name", "role": "What it handles"}},
    {{"tool": "Tool name", "role": "What it handles"}}
  ],
  "cost_estimate": "~$X in API costs",
  "biggest_risk": "The single most likely blocker during execution"
}}

Text: {text}

Output only the JSON above. No markdown wrapper. No explanation."""


def _analyze_one(client: OpenAI, item: RawItem, total: int, done_counter: list, lock: threading.Lock) -> DemandItem | None:
    """Single item: one API call, parse JSON, return DemandItem if score>=6 else None"""
    text = f"{item.title}\n{item.body}"
    try:
        prompt = SCORE_PROMPT.format(tools_str=_tools_str(), text=text[:2000])
        resp = client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = resp.choices[0].message.content or ""
        raw = response_text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        try:
            data = json.loads(raw)
        except Exception as e:
            print(f"[AI] JSON parse failed, raw response: {response_text[:200]}")
            raise
    except Exception as e:
        print(f"[AI] item failed: {type(e).__name__}: {str(e)}")
        with lock:
            done_counter[0] += 1
            print(f"[AI] progress {done_counter[0]}/{total}")
        return None

    score = data.get("commercial_score", 0)
    if isinstance(score, str):
        try:
            score = int(score)
        except ValueError:
            score = 0
    with lock:
        done_counter[0] += 1
        print(f"[AI] progress {done_counter[0]}/{total}")
    if score < AI_MIN_SCORE:
        return None
    tp = data.get("tool_plan") or []
    if not isinstance(tp, list):
        tp = []
    tp = [x for x in tp if isinstance(x, dict) and x.get("tool") and x.get("role")]
    sd = data.get("score_detail") or {}
    if not isinstance(sd, dict):
        sd = {}
    return DemandItem(
        raw=item,
        demand_summary=str(data.get("demand_summary", ""))[:50],
        target_user=str(data.get("target_user", "")),
        commercial_score=score,
        score_reason=str(data.get("score_reason", "")),
        score_detail=sd,
        product_idea=str(data.get("product_idea", "")),
        build_days=str(data.get("build_days", "")),
        tool_plan=tp,
        cost_estimate=str(data.get("cost_estimate", "")),
        biggest_risk=str(data.get("biggest_risk", "")),
    )


def filter_demands(items: list[RawItem], executor: ThreadPoolExecutor | None = None) -> list[DemandItem]:
    """Single-call + concurrent (max_workers=5); items below min score are filtered out"""
    if not DEEPSEEK_API_KEY or deepseek_client is None:
        print("[AI] DEEPSEEK_API_KEY not set, skipping AI filtering")
        return []

    client = deepseek_client
    total = len(items)
    done_counter: list = [0]
    lock = threading.Lock()
    pool = executor or ThreadPoolExecutor(max_workers=5)
    own_executor = executor is None

    try:
        futures = [pool.submit(_analyze_one, client, item, total, done_counter, lock) for item in items]
        results: list[DemandItem] = []
        for future in as_completed(futures):
            try:
                demand = future.result()
                if demand is not None:
                    results.append(demand)
            except Exception as e:
                print(f"[AI] item error: {type(e).__name__}: {str(e)}")
    finally:
        if own_executor:
            pool.shutdown(wait=True)

    results.sort(key=lambda x: x.commercial_score, reverse=True)
    return results
