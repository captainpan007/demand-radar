"""Lemon Squeezy webhook handler."""
import hashlib
import hmac
import json
import os

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select

from database import User, Subscription

router = APIRouter()


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature from Lemon Squeezy."""
    secret = os.getenv("LEMON_SQUEEZY_SIGNING_SECRET", "")
    if not secret:
        return True  # skip in dev when no secret configured
    digest = hmac.new(
        secret.encode(), payload, hashlib.sha256
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
    meta = data.get("meta", {})
    event_name = meta.get("event_name", "")
    attrs = data.get("data", {}).get("attributes", {})

    # Get user email: prefer custom_data (passed via checkout URL), fallback to attributes
    custom_data = meta.get("custom_data", {}) or {}
    user_email = custom_data.get("user_email") or attrs.get("user_email", "")

    lemon_sub_id = str(data.get("data", {}).get("id", ""))
    status = attrs.get("status", "")

    print(f"[webhook] Event: {event_name}, email: {user_email}, status: {status}")

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
