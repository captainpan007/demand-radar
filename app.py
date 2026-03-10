"""FastAPI web application for Demand Radar."""

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as SASession
from starlette.middleware.sessions import SessionMiddleware

from apscheduler.schedulers.background import BackgroundScheduler

import config
from config import SECRET_KEY
from auth import router as auth_router
from database import Session as DBSession
from database import User, init_db, get_session_factory
from pipeline import run_pipeline_sync, run_pipeline
from storage import get_demands_by_date

# Global session factory, initialized on startup
SessionFactory = None

templates = Jinja2Templates(directory="reporter")


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

    now = datetime.now(timezone.utc)
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
        },
    )


@app.post("/admin/run-pipeline")
async def trigger_pipeline():
    """Manual trigger for testing."""
    stats = await run_pipeline(SessionFactory)
    return stats


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
