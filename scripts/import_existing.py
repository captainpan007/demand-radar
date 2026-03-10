"""One-time migration: import existing HTML report files into SQLite.

Parses demand-radar-YYYY-MM-DD.html files from the output/ directory,
extracts demand data from the DOM, and saves to the database via save_demands().

Skips:
- ZH files (same data as EN, but used to populate ZH fields when available)
- Files with 0 demand cards (e.g. 2026-03-07)
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

# Add project root to path so we can import project modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database import init_db, get_session_factory
from models import DemandItem, RawItem
from storage import save_demands

OUTPUT_DIR = PROJECT_ROOT / "output"
# Match EN files only: demand-radar-YYYY-MM-DD.html (no -zh suffix)
EN_FILE_PATTERN = re.compile(r"^demand-radar-(\d{4}-\d{2}-\d{2})\.html$")
ZH_FILE_PATTERN = re.compile(r"^demand-radar-(\d{4}-\d{2}-\d{2})-zh\.html$")


def parse_date_from_filename(filename: str) -> date | None:
    """Extract YYYY-MM-DD date from filename like demand-radar-2026-03-08.html."""
    m = EN_FILE_PATTERN.match(filename)
    if m:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    return None


def parse_score_value(text: str) -> int:
    """Parse '3/3' -> 3, '1/2' -> 1."""
    text = text.strip()
    m = re.match(r"(\d+)/\d+", text)
    return int(m.group(1)) if m else 0


def strip_label_prefix(text: str) -> str:
    """Remove 'Target User: ' or similar label prefix from text."""
    # Handle both EN and ZH label patterns
    if ": " in text:
        return text.split(": ", 1)[1].strip()
    if "：" in text:
        return text.split("：", 1)[1].strip()
    return text.strip()


def extract_after_colon(text: str) -> str:
    """Extract text after first colon, e.g. 'ETA: 7-14 days' -> '7-14 days'."""
    if ": " in text:
        return text.split(": ", 1)[1].strip()
    if "：" in text:
        return text.split("：", 1)[1].strip()
    return text.strip()


def parse_tool_plan(card) -> list[dict]:
    """Extract tool_plan from .tool-tag elements."""
    tools = []
    for tag_el in card.select(".tool-tag"):
        name_el = tag_el.select_one(".tool-name")
        if not name_el:
            continue
        tool_name = name_el.get_text(strip=True)
        # Full text includes "ToolName: role" — extract role part
        full_text = tag_el.get_text(strip=True)
        role = full_text.replace(tool_name, "", 1).strip()
        if role.startswith(":"):
            role = role[1:].strip()
        if role.startswith("："):
            role = role[1:].strip()
        tools.append({"tool": tool_name, "role": role})
    return tools


def parse_card(card, zh_card=None) -> DemandItem:
    """Parse a single <article class='card'> into a DemandItem.

    If zh_card is provided (matching ZH card), populate ZH fields too.
    """
    url = card.get("data-url", "")
    commercial_score = int(card.get("data-score", "0"))

    # Title / demand_summary
    title_el = card.select_one(".card-title")
    demand_summary = title_el.get_text(strip=True) if title_el else ""

    # Source, score, comments from card-row2
    row2_spans = card.select(".card-row2 span")
    source = row2_spans[0].get_text(strip=True) if len(row2_spans) > 0 else ""
    raw_score = 0
    raw_comments = 0
    if len(row2_spans) > 1:
        score_text = row2_spans[1].get_text(strip=True)
        m = re.search(r"(\d+)", score_text)
        raw_score = int(m.group(1)) if m else 0
    if len(row2_spans) > 2:
        comments_text = row2_spans[2].get_text(strip=True)
        m = re.search(r"(\d+)", comments_text)
        raw_comments = int(m.group(1)) if m else 0

    # Product idea
    idea_el = card.select_one(".product-idea")
    product_idea = idea_el.get_text(strip=True) if idea_el else ""

    # Target user
    target_el = card.select_one(".target-user-tag")
    target_user = strip_label_prefix(target_el.get_text(strip=True)) if target_el else ""

    # Score reason
    reason_el = card.select_one(".score-reason-text")
    score_reason = reason_el.get_text(strip=True) if reason_el else ""

    # Score detail from score-grid-value elements
    score_values = card.select(".score-grid-value")
    score_detail = {}
    score_keys = ["pain_level", "payment_signal", "executability", "reach"]
    for i, key in enumerate(score_keys):
        if i < len(score_values):
            score_detail[key] = parse_score_value(score_values[i].get_text(strip=True))

    # Build days
    build_el = card.select_one(".build-days")
    build_days = extract_after_colon(build_el.get_text(strip=True)) if build_el else ""

    # Tool plan
    tool_plan = parse_tool_plan(card)

    # Cost estimate
    cost_el = card.select_one(".cost-estimate")
    cost_estimate = extract_after_colon(cost_el.get_text(strip=True)) if cost_el else ""

    # Biggest risk
    risk_el = card.select_one(".biggest-risk")
    biggest_risk = extract_after_colon(risk_el.get_text(strip=True)) if risk_el else ""

    # ZH fields (from matching ZH card)
    demand_summary_zh = ""
    target_user_zh = ""
    product_idea_zh = ""
    score_reason_zh = ""
    build_days_zh = ""
    tool_plan_zh = []
    cost_estimate_zh = ""
    biggest_risk_zh = ""

    if zh_card is not None:
        zh_title_el = zh_card.select_one(".card-title")
        demand_summary_zh = zh_title_el.get_text(strip=True) if zh_title_el else ""

        zh_target_el = zh_card.select_one(".target-user-tag")
        target_user_zh = strip_label_prefix(zh_target_el.get_text(strip=True)) if zh_target_el else ""

        zh_idea_el = zh_card.select_one(".product-idea")
        product_idea_zh = zh_idea_el.get_text(strip=True) if zh_idea_el else ""

        zh_reason_el = zh_card.select_one(".score-reason-text")
        score_reason_zh = zh_reason_el.get_text(strip=True) if zh_reason_el else ""

        zh_build_el = zh_card.select_one(".build-days")
        build_days_zh = extract_after_colon(zh_build_el.get_text(strip=True)) if zh_build_el else ""

        tool_plan_zh = parse_tool_plan(zh_card)

        zh_cost_el = zh_card.select_one(".cost-estimate")
        cost_estimate_zh = extract_after_colon(zh_cost_el.get_text(strip=True)) if zh_cost_el else ""

        zh_risk_el = zh_card.select_one(".biggest-risk")
        biggest_risk_zh = extract_after_colon(zh_risk_el.get_text(strip=True)) if zh_risk_el else ""

    raw = RawItem(
        source=source,
        title=demand_summary,  # best we have from HTML
        body="",  # original body not in the HTML
        url=url,
        score=raw_score,
        comments=raw_comments,
    )

    return DemandItem(
        raw=raw,
        demand_summary=demand_summary,
        target_user=target_user,
        commercial_score=commercial_score,
        score_reason=score_reason,
        product_idea=product_idea,
        build_days=build_days,
        tool_plan=tool_plan,
        score_detail=score_detail,
        cost_estimate=cost_estimate,
        biggest_risk=biggest_risk,
        demand_summary_zh=demand_summary_zh,
        target_user_zh=target_user_zh,
        product_idea_zh=product_idea_zh,
        score_reason_zh=score_reason_zh,
        build_days_zh=build_days_zh,
        tool_plan_zh=tool_plan_zh,
        cost_estimate_zh=cost_estimate_zh,
        biggest_risk_zh=biggest_risk_zh,
    )


def parse_html_file(filepath: Path) -> list:
    """Parse an HTML report file and return list of BeautifulSoup card elements."""
    html = filepath.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    return soup.select("article.card")


def build_zh_lookup(zh_cards: list) -> dict:
    """Build a dict mapping data-url -> zh card element for quick lookup."""
    return {card.get("data-url", ""): card for card in zh_cards if card.get("data-url")}


def main():
    print("=" * 60)
    print("Demand Radar — Import Existing HTML Reports")
    print("=" * 60)

    # Find EN HTML files
    en_files = []
    for f in sorted(OUTPUT_DIR.iterdir()):
        m = EN_FILE_PATTERN.match(f.name)
        if m:
            report_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            en_files.append((f, report_date))

    if not en_files:
        print("No EN HTML files found in", OUTPUT_DIR)
        return

    # Init DB
    engine = init_db()
    session_factory = get_session_factory(engine)

    total_imported = 0

    for en_path, report_date in en_files:
        date_str = report_date.isoformat()
        print(f"\n--- {en_path.name} (date: {date_str}) ---")

        # Parse EN cards
        en_cards = parse_html_file(en_path)
        if not en_cards:
            print(f"  No demand cards found, skipping.")
            continue

        # Check for matching ZH file
        zh_path = OUTPUT_DIR / f"demand-radar-{date_str}-zh.html"
        zh_lookup = {}
        if zh_path.exists():
            zh_cards = parse_html_file(zh_path)
            zh_lookup = build_zh_lookup(zh_cards)
            print(f"  Found ZH file with {len(zh_cards)} cards.")

        # Parse each card into DemandItem
        items = []
        for card in en_cards:
            card_url = card.get("data-url", "")
            zh_card = zh_lookup.get(card_url)
            item = parse_card(card, zh_card)
            items.append(item)

        # Save to DB
        session = session_factory()
        try:
            count = save_demands(session, items, report_date=report_date)
            print(f"  Parsed {len(items)} cards, imported {count} new demands.")
            total_imported += count
        finally:
            session.close()

    print(f"\n{'=' * 60}")
    print(f"Done. Total imported: {total_imported} demands.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
