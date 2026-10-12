"""База: таблица tickets. Пишем все принятые обращения, включая сбои модели."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app import config


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    client_id: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32))
    draft_reply: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(16))
    escalate: Mapped[bool] = mapped_column(Boolean)
    error: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)


_engine = None
_session_factory = None


def init_db(url: str | None = None) -> None:
    """Создаёт соединение и таблицы. Повторный вызов с другим url (в тестах) заменяет базу."""
    global _engine, _session_factory
    url = url or config.database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, connect_args=connect_args)
    Base.metadata.create_all(_engine)
    _session_factory = sessionmaker(_engine, expire_on_commit=False)


def session() -> Session:
    if _session_factory is None:
        init_db()
    return _session_factory()


def save_ticket(**fields) -> Ticket:
    with session() as db:
        ticket = Ticket(created_at=datetime.now(timezone.utc), **fields)
        db.add(ticket)
        db.commit()
        return ticket


def recent_tickets(client_id: str, window_seconds: int = 60) -> list[datetime]:
    """Время принятых обращений клиента за последнее окно, от старого к новому."""
    since = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    with session() as db:
        rows = db.scalars(
            select(Ticket.created_at)
            .where(Ticket.client_id == client_id, Ticket.created_at > since)
            .order_by(Ticket.created_at)
        ).all()
    # SQLite отдаёт время без часового пояса: считаем его UTC
    return [row if row.tzinfo else row.replace(tzinfo=timezone.utc) for row in rows]


def count_tickets() -> int:
    with session() as db:
        return db.scalar(select(func.count()).select_from(Ticket))
