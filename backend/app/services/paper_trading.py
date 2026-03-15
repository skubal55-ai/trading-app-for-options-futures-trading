import uuid
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

paper_positions: list[dict] = []
paper_orders: list[dict] = []
paper_portfolio = {
    "balance": 1000000.0,
    "initial_balance": 1000000.0,
    "total_pnl": 0.0,
    "total_pnl_percent": 0.0,
    "open_positions": 0,
    "closed_positions": 0,
    "winning_trades": 0,
    "losing_trades": 0,
}

auto_trade_settings = {
    "enabled": False,
    "mode": "PAPER",
    "strategies": [],
    "max_trades_per_day": 5,
    "max_capital_per_trade": 10000.0,
    "stop_loss_percent": 2.0,
    "target_percent": 4.0,
    "segments": ["EQUITY"],
    "trading_start_time": "09:15",
    "trading_end_time": "15:15",
}


def place_order(
    symbol: str,
    trade_type: str,
    order_type: str,
    quantity: int,
    price: float,
    stop_loss: Optional[float] = None,
    target: Optional[float] = None,
    segment: str = "EQUITY",
    mode: str = "PAPER",
) -> dict:
    order_id = str(uuid.uuid4())[:8]
    total_cost = price * quantity

    if mode == "PAPER":
        if trade_type == "BUY" and total_cost > paper_portfolio["balance"]:
            return {"error": "Insufficient balance", "required": total_cost, "available": paper_portfolio["balance"]}

        order = {
            "id": order_id,
            "symbol": symbol,
            "trade_type": trade_type,
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
            "stop_loss": stop_loss,
            "target": target,
            "segment": segment,
            "mode": mode,
            "status": "EXECUTED",
            "timestamp": datetime.now().isoformat(),
        }
        paper_orders.append(order)

        if trade_type == "BUY":
            paper_portfolio["balance"] -= total_cost
            position = {
                "id": order_id,
                "symbol": symbol,
                "trade_type": trade_type,
                "entry_price": price,
                "current_price": price,
                "quantity": quantity,
                "pnl": 0.0,
                "pnl_percent": 0.0,
                "stop_loss": stop_loss,
                "target": target,
                "segment": segment,
                "mode": mode,
                "status": "OPEN",
                "timestamp": datetime.now().isoformat(),
            }
            paper_positions.append(position)
            paper_portfolio["open_positions"] += 1
        else:
            open_pos = [p for p in paper_positions if p["symbol"] == symbol and p["status"] == "OPEN"]
            if open_pos:
                pos = open_pos[0]
                pnl = (price - pos["entry_price"]) * pos["quantity"]
                pos["current_price"] = price
                pos["pnl"] = round(pnl, 2)
                pos["pnl_percent"] = round((pnl / (pos["entry_price"] * pos["quantity"])) * 100, 2)
                pos["status"] = "CLOSED"
                paper_portfolio["balance"] += price * pos["quantity"]
                paper_portfolio["open_positions"] -= 1
                paper_portfolio["closed_positions"] += 1
                paper_portfolio["total_pnl"] += pnl
                if pnl > 0:
                    paper_portfolio["winning_trades"] += 1
                else:
                    paper_portfolio["losing_trades"] += 1

        paper_portfolio["total_pnl_percent"] = round(
            (paper_portfolio["total_pnl"] / paper_portfolio["initial_balance"]) * 100, 2
        )

        return order
    else:
        return {
            "id": order_id,
            "symbol": symbol,
            "trade_type": trade_type,
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
            "stop_loss": stop_loss,
            "target": target,
            "segment": segment,
            "mode": mode,
            "status": "PENDING_BROKER_CONNECTION",
            "message": "Live trading requires broker API integration. Please configure your broker credentials in settings.",
            "timestamp": datetime.now().isoformat(),
        }


def get_positions(mode: str = "PAPER", status: str = "ALL") -> list[dict]:
    positions = paper_positions
    if status != "ALL":
        positions = [p for p in positions if p["status"] == status]
    return positions


def get_portfolio() -> dict:
    invested = sum(
        p["entry_price"] * p["quantity"]
        for p in paper_positions
        if p["status"] == "OPEN"
    )
    paper_portfolio["invested_value"] = round(invested, 2)
    paper_portfolio["available_balance"] = round(paper_portfolio["balance"], 2)
    return paper_portfolio


def get_orders() -> list[dict]:
    return paper_orders


def update_positions_with_live_price(symbol: str, current_price: float) -> None:
    for pos in paper_positions:
        if pos["symbol"] == symbol and pos["status"] == "OPEN":
            pnl = (current_price - pos["entry_price"]) * pos["quantity"]
            pos["current_price"] = current_price
            pos["pnl"] = round(pnl, 2)
            pos["pnl_percent"] = round((pnl / (pos["entry_price"] * pos["quantity"])) * 100, 2)

            if pos["stop_loss"] and current_price <= pos["stop_loss"]:
                pos["status"] = "SL_HIT"
                paper_portfolio["balance"] += current_price * pos["quantity"]
                paper_portfolio["open_positions"] -= 1
                paper_portfolio["closed_positions"] += 1
                paper_portfolio["total_pnl"] += pnl
                paper_portfolio["losing_trades"] += 1

            if pos["target"] and current_price >= pos["target"]:
                pos["status"] = "TARGET_HIT"
                paper_portfolio["balance"] += current_price * pos["quantity"]
                paper_portfolio["open_positions"] -= 1
                paper_portfolio["closed_positions"] += 1
                paper_portfolio["total_pnl"] += pnl
                paper_portfolio["winning_trades"] += 1


def reset_paper_trading() -> dict:
    paper_positions.clear()
    paper_orders.clear()
    paper_portfolio.update({
        "balance": 1000000.0,
        "initial_balance": 1000000.0,
        "total_pnl": 0.0,
        "total_pnl_percent": 0.0,
        "open_positions": 0,
        "closed_positions": 0,
        "winning_trades": 0,
        "losing_trades": 0,
    })
    return {"message": "Paper trading account reset successfully"}


def get_auto_trade_settings() -> dict:
    return auto_trade_settings


def update_auto_trade_settings(settings: dict) -> dict:
    auto_trade_settings.update(settings)
    return auto_trade_settings
