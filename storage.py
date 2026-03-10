"""Storage layer: convert between DemandItem dataclass and DB Demand model."""

import json
from datetime import date, datetime

from sqlalchemy import text

from database import Demand
from models import DemandItem, RawItem


def _row_to_demand_item(row: Demand) -> DemandItem:
    """Convert a DB Demand row back into a DemandItem dataclass."""
    raw = RawItem(
        source=row.source or "",
        title=row.title or "",
        body=row.body or "",
        url=row.url or "",
        score=row.score or 0,
        comments=row.comments or 0,
    )

    # Parse JSON fields
    tool_plan = []
    if row.tool_plan:
        try:
            tool_plan = json.loads(row.tool_plan)
        except (json.JSONDecodeError, TypeError):
            pass

    tool_plan_zh = []
    if row.tool_plan_zh:
        try:
            tool_plan_zh = json.loads(row.tool_plan_zh)
        except (json.JSONDecodeError, TypeError):
            pass

    score_detail = {}
    if row.score_detail:
        try:
            score_detail = json.loads(row.score_detail)
        except (json.JSONDecodeError, TypeError):
            pass

    return DemandItem(
        raw=raw,
        demand_summary=row.demand_summary or "",
        target_user=row.target_user or "",
        commercial_score=row.commercial_score or 0,
        score_reason=row.score_reason or "",
        product_idea=row.product_idea or "",
        build_days=row.build_days or "",
        tool_plan=tool_plan,
        score_detail=score_detail,
        cost_estimate=row.cost_estimate or "",
        biggest_risk=row.biggest_risk or "",
        demand_summary_zh=row.demand_summary_zh or "",
        target_user_zh=row.target_user_zh or "",
        product_idea_zh=row.product_idea_zh or "",
        score_reason_zh=row.score_reason_zh or "",
        build_days_zh=row.build_days_zh or "",
        tool_plan_zh=tool_plan_zh,
        cost_estimate_zh=row.cost_estimate_zh or "",
        biggest_risk_zh=row.biggest_risk_zh or "",
    )


def save_demands(session, items: list[DemandItem], report_date=None) -> int:
    """Save DemandItem list to DB. Skip duplicates by url+date. Return count of new rows."""
    if report_date is None:
        report_date = date.today()

    # Get existing urls for this date to skip duplicates
    existing = session.execute(
        text("SELECT url FROM demands WHERE report_date = :d"),
        {"d": report_date},
    )
    existing_urls = {row[0] for row in existing}

    new_count = 0
    for item in items:
        url = item.raw.url
        if url in existing_urls:
            continue

        row = Demand(
            report_date=report_date,
            source=item.raw.source,
            title=item.raw.title,
            body=item.raw.body,
            url=url,
            score=item.raw.score,
            comments=item.raw.comments,
            demand_summary=item.demand_summary,
            target_user=item.target_user,
            commercial_score=item.commercial_score,
            score_detail=json.dumps(item.score_detail) if item.score_detail else None,
            score_reason=item.score_reason,
            product_idea=item.product_idea,
            build_days=item.build_days,
            tool_plan=json.dumps(item.tool_plan) if item.tool_plan else None,
            cost_estimate=item.cost_estimate,
            biggest_risk=item.biggest_risk,
            demand_summary_zh=item.demand_summary_zh,
            target_user_zh=item.target_user_zh,
            product_idea_zh=item.product_idea_zh,
            score_reason_zh=item.score_reason_zh,
            build_days_zh=item.build_days_zh,
            tool_plan_zh=json.dumps(item.tool_plan_zh) if item.tool_plan_zh else None,
            cost_estimate_zh=item.cost_estimate_zh,
            biggest_risk_zh=item.biggest_risk_zh,
        )
        session.add(row)
        session.flush()  # get the row id

        # Update FTS index
        session.execute(
            text(
                "INSERT INTO demands_fts(rowid, demand_summary, product_idea, body, target_user) "
                "VALUES (:rowid, :demand_summary, :product_idea, :body, :target_user)"
            ),
            {
                "rowid": row.id,
                "demand_summary": item.demand_summary or "",
                "product_idea": item.product_idea or "",
                "body": item.raw.body or "",
                "target_user": item.target_user or "",
            },
        )

        existing_urls.add(url)
        new_count += 1

    session.commit()
    return new_count


def get_demands_by_date(session, report_date: date) -> list[DemandItem]:
    """Get all demands for a date, sorted by commercial_score desc."""
    rows = (
        session.query(Demand)
        .filter(Demand.report_date == report_date)
        .order_by(Demand.commercial_score.desc())
        .all()
    )
    return [_row_to_demand_item(r) for r in rows]


def get_available_dates(session) -> list[date]:
    """Get all distinct dates that have demands, newest first."""
    result = session.execute(
        text("SELECT DISTINCT report_date FROM demands ORDER BY report_date DESC")
    )
    return [row[0] if isinstance(row[0], date) else datetime.strptime(row[0], "%Y-%m-%d").date() for row in result]


def search_demands(session, query: str, limit: int = 50) -> list[DemandItem]:
    """FTS5 search across demand_summary, product_idea, body, target_user.

    Results sorted by commercial_score desc.
    """
    result = session.execute(
        text(
            "SELECT d.* FROM demands d "
            "JOIN demands_fts fts ON d.id = fts.rowid "
            "WHERE demands_fts MATCH :query "
            "ORDER BY d.commercial_score DESC "
            "LIMIT :limit"
        ),
        {"query": query, "limit": limit},
    )
    rows = result.fetchall()

    # Convert raw rows to Demand objects
    items = []
    for row in rows:
        demand = Demand()
        for i, col in enumerate(result.keys()):
            setattr(demand, col, row[i])
        items.append(_row_to_demand_item(demand))
    return items
