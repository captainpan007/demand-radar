"""SQLAlchemy 2.0 database models and initialization for Demand Radar."""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_PATH = Path(__file__).parent / "data" / "demand_radar.db"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    google_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    tier: Mapped[str] = mapped_column(String, default="free", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )


class Session(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    lemon_subscription_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow(), nullable=False
    )


class Demand(Base):
    __tablename__ = "demands"
    __table_args__ = (
        Index("idx_demands_date", "report_date"),
        Index("idx_demands_score", "commercial_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    demand_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    commercial_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_idea: Mapped[str | None] = mapped_column(Text, nullable=True)
    build_days: Mapped[str | None] = mapped_column(String, nullable=True)
    tool_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_estimate: Mapped[str | None] = mapped_column(String, nullable=True)
    biggest_risk: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Chinese translations
    demand_summary_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_user_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_idea_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_reason_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    build_days_zh: Mapped[str | None] = mapped_column(String, nullable=True)
    tool_plan_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_estimate_zh: Mapped[str | None] = mapped_column(String, nullable=True)
    biggest_risk_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow(), nullable=False
    )


def get_engine():
    """Create SQLite engine at data/demand_radar.db with WAL mode and foreign keys."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def init_db(engine=None):
    """Create all tables and the FTS5 virtual table. Returns the engine."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)

    fts_sql = text(
        "CREATE VIRTUAL TABLE IF NOT EXISTS demands_fts USING fts5("
        "demand_summary, product_idea, body, target_user, "
        "content='demands', content_rowid='id')"
    )
    with engine.connect() as conn:
        conn.execute(fts_sql)
        conn.commit()

    return engine


def get_session_factory(engine=None):
    """Return a sessionmaker bound to the given or default engine."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)
