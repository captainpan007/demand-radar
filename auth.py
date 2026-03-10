"""Google OAuth routes."""
import secrets
from datetime import datetime, timedelta, timezone

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, BASE_URL
from database import User, Session as DBSession, get_session_factory

router = APIRouter(prefix="/auth")

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google")
async def google_login(request: Request):
    redirect_uri = f"{BASE_URL}/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def google_callback(request: Request):
    from app import SessionFactory
    token_data = await oauth.google.authorize_access_token(request)
    userinfo = token_data.get("userinfo")
    if not userinfo:
        return RedirectResponse("/")

    db = SessionFactory()
    try:
        # Find or create user
        user = db.execute(
            select(User).where(User.google_id == str(userinfo["sub"]))
        ).scalar_one_or_none()

        if not user:
            user = User(
                google_id=str(userinfo["sub"]),
                email=userinfo.get("email", ""),
                name=userinfo.get("name", ""),
                avatar_url=userinfo.get("picture", ""),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.name = userinfo.get("name", user.name)
            user.avatar_url = userinfo.get("picture", user.avatar_url)
            user.updated_at = datetime.now(timezone.utc)
            db.commit()

        # Create session
        session_token = secrets.token_urlsafe(32)
        db_sess = DBSession(
            token=session_token,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(db_sess)
        db.commit()
    finally:
        db.close()

    response = RedirectResponse("/")
    response.set_cookie(
        "session_token", session_token,
        max_age=30 * 24 * 3600, httponly=True, samesite="lax",
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    from app import SessionFactory
    token = request.cookies.get("session_token")
    if token:
        db = SessionFactory()
        try:
            sess = db.execute(
                select(DBSession).where(DBSession.token == token)
            ).scalar_one_or_none()
            if sess:
                db.delete(sess)
                db.commit()
        finally:
            db.close()

    response = RedirectResponse("/")
    response.delete_cookie("session_token")
    return response
