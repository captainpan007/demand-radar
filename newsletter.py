"""Weekly newsletter: select top demands, render email, send via Resend."""

import logging
from datetime import date, timedelta

import resend
from jinja2 import Environment, FileSystemLoader

from config import RESEND_API_KEY, NEWSLETTER_FROM_EMAIL
from database import User
from storage import get_weekly_top_demands

logger = logging.getLogger(__name__)

_jinja_env = Environment(
    loader=FileSystemLoader("reporter"),
    autoescape=True,
)


def _get_pro_emails(session) -> list[str]:
    """Return email addresses of all tier=pro users."""
    users = session.query(User).filter(User.tier == "pro").all()
    return [u.email for u in users if u.email]


def _render_newsletter(items, date_range: str) -> str:
    """Render the newsletter HTML from template."""
    template = _jinja_env.get_template("newsletter_template.html")
    return template.render(
        items=items,
        item_count=len(items),
        date_range=date_range,
    )


def _send_one(to_email: str, subject: str, html: str) -> bool:
    """Send one email via Resend. Retry once on failure. Returns True on success."""
    for attempt in range(2):
        try:
            resend.Emails.send({
                "from": NEWSLETTER_FROM_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html,
            })
            return True
        except Exception as e:
            if attempt == 0:
                logger.warning(f"[Newsletter] retry for {to_email}: {e}")
            else:
                logger.error(f"[Newsletter] failed for {to_email} after retry: {e}")
    return False


def send_weekly_newsletter(session_factory) -> dict:
    """Main entry point: select top 10, render, send to all pro users.

    Returns dict with keys: recipients, sent, failed, item_count
    """
    if not RESEND_API_KEY:
        logger.error("[Newsletter] RESEND_API_KEY not set, skipping")
        return {"recipients": 0, "sent": 0, "failed": 0, "item_count": 0}

    resend.api_key = RESEND_API_KEY

    db = session_factory()
    try:
        # Select top 10 from past week
        today = date.today()
        items = get_weekly_top_demands(db, end_date=today, top_n=10)
        if not items:
            logger.info("[Newsletter] No demands found for this week, skipping")
            return {"recipients": 0, "sent": 0, "failed": 0, "item_count": 0}

        # Date range string
        start_date = today - timedelta(days=6)
        date_range = f"{start_date.isoformat()} ~ {today.isoformat()}"

        # Render
        subject = f"Demand Radar Weekly Top 10 ({date_range})"
        html = _render_newsletter(items, date_range)

        # Get recipients
        emails = _get_pro_emails(db)
        if not emails:
            logger.info("[Newsletter] No pro users found, skipping")
            return {"recipients": 0, "sent": 0, "failed": 0, "item_count": len(items)}

        # Send
        sent = 0
        failed = 0
        for email in emails:
            if _send_one(email, subject, html):
                sent += 1
            else:
                failed += 1

        logger.info(f"[Newsletter] Done: {sent} sent, {failed} failed, {len(items)} items")
        return {"recipients": len(emails), "sent": sent, "failed": failed, "item_count": len(items)}

    finally:
        db.close()
