"""FastAPI web application for Demand Radar."""

import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as SASession
from starlette.middleware.sessions import SessionMiddleware

from apscheduler.schedulers.background import BackgroundScheduler

import config
from config import SECRET_KEY
from auth import router as auth_router
from webhook import router as webhook_router
from database import Session as DBSession
from database import User, init_db, get_session_factory
from pipeline import run_pipeline_sync, run_pipeline
from storage import get_demands_by_date, get_available_dates

# Global session factory, initialized on startup
SessionFactory = None

templates = Jinja2Templates(directory="reporter")


def truncate_words(text: str, max_chars: int = 90) -> str:
    """Truncate text at a word boundary, never mid-word."""
    if not text or len(text) <= max_chars:
        return text or ""
    cut = text[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > max_chars * 0.3:
        cut = cut[:last_space]
    cut = cut.rstrip(" ,;:-")
    return cut + "..."


templates.env.filters["truncate_words"] = truncate_words


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and session factory on startup."""
    global SessionFactory
    engine = init_db()
    SessionFactory = get_session_factory(engine)
    print("[app] Database initialized")

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_pipeline_sync, "cron", hour=6, minute=0,
        args=[SessionFactory], id="daily_scrape",
    )
    scheduler.start()
    print("[app] Scheduler started (daily at 06:00 UTC)")

    yield

    scheduler.shutdown()


app = FastAPI(title="Demand Radar", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.include_router(auth_router)
app.include_router(webhook_router)


def get_db():
    """Dependency that yields a DB session."""
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: SASession = Depends(get_db)):
    """Read session_token cookie and return user dict or None."""
    token = request.cookies.get("session_token")
    if not token:
        return None

    now = datetime.utcnow()
    db_session = db.query(DBSession).filter(DBSession.token == token).first()
    if not db_session or db_session.expires_at < now:
        return None

    user = db.query(User).filter(User.id == db_session.user_id).first()
    if not user:
        return None

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "tier": user.tier,
    }


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    lang: str = "en",
    db: SASession = Depends(get_db),
):
    """Index route: show today's demands with tier-based limits."""
    user = get_current_user(request, db)

    today = date.today()
    all_items = get_demands_by_date(db, today)
    total = len(all_items)

    # Determine tier and apply limit
    if user is None:
        tier = "visitor"
        limit = config.VISITOR_LIMIT
    elif user["tier"] == "pro":
        tier = "pro"
        limit = None
    else:
        tier = "free"
        limit = config.FREE_LIMIT

    is_visitor = tier == "visitor"
    is_free = tier == "free"
    is_pro = tier == "pro"

    if limit is not None:
        items = all_items[:limit]
        has_more = total > limit
        blurred_count = total - limit if has_more else 0
    else:
        items = all_items
        has_more = False
        blurred_count = 0

    # Pro user extras
    available_dates = []
    current_date = today.isoformat()
    if is_pro:
        available_dates = [d.isoformat() for d in get_available_dates(db)]

    # Language switch URL
    other_lang = "zh" if lang == "en" else "en"
    lang_switch_url = f"/?lang={other_lang}"

    return templates.TemplateResponse(
        "template.html",
        {
            "request": request,
            "date": today.isoformat(),
            "total": total,
            "count": len(items),
            "items": items,
            "lang": lang,
            "lang_switch_url": lang_switch_url,
            "user": user,
            "has_more": has_more,
            "blurred_count": blurred_count,
            "is_visitor": is_visitor,
            "is_free": is_free,
            "is_pro": is_pro,
            "available_dates": available_dates,
            "current_date": current_date,
        },
    )


@app.get("/history", response_class=HTMLResponse)
async def history(
    request: Request,
    date: str = "",
    lang: str = "en",
    db: SASession = Depends(get_db),
):
    """Historical reports for pro users."""
    user = get_current_user(request, db)
    if not user or user["tier"] != "pro":
        return RedirectResponse("/pricing")

    from datetime import date as date_type
    try:
        report_date = date_type.fromisoformat(date) if date else date_type.today()
    except ValueError:
        report_date = date_type.today()

    all_items = get_demands_by_date(db, report_date)
    available_dates = [d.isoformat() for d in get_available_dates(db)]

    other_lang = "zh" if lang == "en" else "en"
    lang_switch_url = f"/history?date={report_date.isoformat()}&lang={other_lang}"

    return templates.TemplateResponse(
        "template.html",
        {
            "request": request,
            "date": report_date.isoformat(),
            "total": len(all_items),
            "count": len(all_items),
            "items": all_items,
            "lang": lang,
            "lang_switch_url": lang_switch_url,
            "user": user,
            "has_more": False,
            "blurred_count": 0,
            "is_visitor": False,
            "is_free": False,
            "is_pro": True,
            "available_dates": available_dates,
            "current_date": report_date.isoformat(),
        },
    )


@app.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = "",
    lang: str = "en",
    db: SASession = Depends(get_db),
):
    """Search demands for pro users."""
    user = get_current_user(request, db)
    if not user or user["tier"] != "pro":
        return RedirectResponse("/pricing")

    results = []
    if q.strip():
        from storage import search_demands
        results = search_demands(db, q.strip(), limit=50)

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "query": q,
            "results": results,
            "count": len(results),
            "lang": lang,
            "user": user,
            "is_pro": True,
        },
    )


@app.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request, db: SASession = Depends(get_db)):
    """Pricing page."""
    user = get_current_user(request, db)
    return templates.TemplateResponse(
        "pricing.html",
        {
            "request": request,
            "user": user,
            "is_pro": user is not None and user["tier"] == "pro",
            "checkout_url": config.LEMON_SQUEEZY_CHECKOUT_URL,
            "base_url": config.BASE_URL,
        },
    )


ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")


def _check_admin(request: Request):
    """Verify admin access via Bearer token."""
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Admin not configured")
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(status_code=403, detail="Forbidden")


@app.post("/admin/run-pipeline")
async def trigger_pipeline(request: Request):
    """Manual trigger for testing. Requires ADMIN_TOKEN."""
    _check_admin(request)
    stats = await run_pipeline(SessionFactory)
    return stats


@app.post("/admin/rerun-today")
async def rerun_today(request: Request):
    """Delete today's data and re-run pipeline. Requires ADMIN_TOKEN."""
    _check_admin(request)
    from database import Demand
    db = SessionFactory()
    try:
        today = date.today()
        deleted = db.query(Demand).filter(Demand.report_date == today).delete()
        db.commit()
    finally:
        db.close()
    stats = await run_pipeline(SessionFactory)
    return {"deleted": deleted, **stats}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
