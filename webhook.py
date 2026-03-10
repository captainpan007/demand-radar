"""Lemon Squeezy webhook handler."""
import hashlib
import hmac
import json

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select

from config import LEMON_SQUEEZY_SIGNING_SECRET
from database import User, Subscription

router = APIRouter()


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature from Lemon Squeezy."""
    if not LEMON_SQUEEZY_SIGNING_SECRET:
        return True  # skip in dev when no secret configured
    digest = hmac.new(
        LEMON_SQUEEZY_SIGNING_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


@router.post("/webhook/lemon")
async def lemon_webhook(request: Request):
    """Handle Lemon Squeezy subscription events."""
    from app import SessionFactory

    body = await request.body()
    signature = request.headers.get("X-Signature", "")

    if not verify_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = json.loads(body)
    event_name = data.get("meta", {}).get("event_name", "")
    attrs = data.get("data", {}).get("attributes", {})
    user_email = attrs.get("user_email", "")
    lemon_sub_id = str(data.get("data", {}).get("id", ""))
    status = attrs.get("status", "")

    db = SessionFactory()
    try:
        user = db.execute(
            select(User).where(User.email == user_email)
        ).scalar_one_or_none()
        if not user:
            print(f"[webhook] No user for email: {user_email}")
            return {"ok": True}

        if event_name == "subscription_created":
            sub = Subscription(
                user_id=user.id,
                lemon_subscription_id=lemon_sub_id,
                status="active",
            )
            db.add(sub)
            user.tier = "pro"
            db.commit()
            print(f"[webhook] User {user_email} upgraded to pro")

        elif event_name == "subscription_updated":
            sub = db.execute(
                select(Subscription).where(
                    Subscription.lemon_subscription_id == lemon_sub_id
                )
            ).scalar_one_or_none()
            if sub:
                sub.status = status
            if status in ("active", "on_trial"):
                user.tier = "pro"
            elif status in ("cancelled", "expired", "past_due"):
                user.tier = "free"
            db.commit()
            print(f"[webhook] User {user_email} subscription updated: {status}")

        elif event_name == "subscription_expired":
            user.tier = "free"
            sub = db.execute(
                select(Subscription).where(
                    Subscription.lemon_subscription_id == lemon_sub_id
                )
            ).scalar_one_or_none()
            if sub:
                sub.status = "expired"
            db.commit()
            print(f"[webhook] User {user_email} subscription expired")

    finally:
        db.close()

    return {"ok": True}
