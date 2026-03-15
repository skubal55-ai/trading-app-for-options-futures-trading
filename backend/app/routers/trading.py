from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services.paper_trading import (
    place_order,
    get_positions,
    get_portfolio,
    get_orders,
    reset_paper_trading,
    get_auto_trade_settings,
    update_auto_trade_settings,
)

router = APIRouter(prefix="/api/trading", tags=["Trading"])


class OrderRequest(BaseModel):
    symbol: str
    trade_type: str
    order_type: str = "MARKET"
    quantity: int
    price: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    segment: str = "EQUITY"
    mode: str = "PAPER"


class AutoTradeSettingsRequest(BaseModel):
    enabled: bool = False
    mode: str = "PAPER"
    strategies: list[str] = []
    max_trades_per_day: int = 5
    max_capital_per_trade: float = 10000.0
    stop_loss_percent: float = 2.0
    target_percent: float = 4.0
    segments: list[str] = ["EQUITY"]
    trading_start_time: str = "09:15"
    trading_end_time: str = "15:15"


@router.post("/order")
async def create_order(order: OrderRequest):
    result = place_order(
        symbol=order.symbol.upper(),
        trade_type=order.trade_type,
        order_type=order.order_type,
        quantity=order.quantity,
        price=order.price,
        stop_loss=order.stop_loss,
        target=order.target,
        segment=order.segment,
        mode=order.mode,
    )
    return result


@router.get("/positions")
async def positions(status: str = "ALL"):
    return {"positions": get_positions(status=status)}


@router.get("/portfolio")
async def portfolio():
    return get_portfolio()


@router.get("/orders")
async def orders():
    return {"orders": get_orders()}


@router.post("/reset")
async def reset():
    return reset_paper_trading()


@router.get("/auto-trade/settings")
async def auto_settings():
    return get_auto_trade_settings()


@router.post("/auto-trade/settings")
async def update_auto_settings(settings: AutoTradeSettingsRequest):
    return update_auto_trade_settings(settings.model_dump())
