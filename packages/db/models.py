from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .session import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument: Mapped[str] = mapped_column(String(64), index=True)
    segment: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(8))
    entry: Mapped[float] = mapped_column(Float)
    stop: Mapped[float] = mapped_column(Float)
    target: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    explanation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    broker: Mapped[str] = mapped_column(String(32), index=True)
    broker_order_id: Mapped[str] = mapped_column(String(96), index=True)
    instrument: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    avg_price: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TradeJournal(Base):
    __tablename__ = "trade_journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    note: Mapped[str] = mapped_column(Text)
    pnl: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
