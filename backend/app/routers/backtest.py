"""
Backtesting Router - API endpoints for running strategy backtests
and viewing historical trade performance.
"""

from fastapi import APIRouter, Query
from typing import Optional
from app.services.backtester import run_backtest

router = APIRouter(prefix="/api/backtest", tags=["Backtesting"])


@router.get("/run")
async def run_strategy_backtest(
    strategy: str = Query(default="MA_CROSSOVER", description="Strategy to backtest"),
    period: str = Query(default="1y", description="Historical period (6mo, 1y, 2y)"),
    holding_days: int = Query(default=10, description="Max holding period in days"),
    capital: float = Query(default=100000, description="Starting capital"),
    symbols: Optional[str] = Query(default=None, description="Comma-separated symbols (defaults to NIFTY50 top 15)"),
):
    """Run a backtest for a given strategy over historical data."""
    symbol_list = None
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]

    result = run_backtest(
        symbols=symbol_list,
        strategy=strategy,
        period=period,
        holding_days=holding_days,
        capital=capital,
    )
    return result


@router.get("/strategies")
async def backtest_strategies():
    """List strategies available for backtesting."""
    return {
        "strategies": [
            {"id": "MA_CROSSOVER", "name": "Moving Average Crossover", "type": "Equity"},
            {"id": "RSI_DIVERGENCE", "name": "RSI Divergence", "type": "Equity"},
            {"id": "MACD_SIGNAL", "name": "MACD Signal", "type": "Equity"},
            {"id": "BOLLINGER_BREAKOUT", "name": "Bollinger Breakout", "type": "Equity"},
            {"id": "SUPERTREND", "name": "Supertrend", "type": "Equity"},
            {"id": "VOLUME_BREAKOUT", "name": "Volume Breakout", "type": "Equity"},
            {"id": "EMA_RIBBON", "name": "EMA Ribbon", "type": "Equity"},
            {"id": "LONG_CALL", "name": "Long Call", "type": "Options - Call"},
            {"id": "BULL_CALL_SPREAD", "name": "Bull Call Spread", "type": "Options - Call"},
            {"id": "CALL_RATIO_BACKSPREAD", "name": "Call Ratio Backspread", "type": "Options - Call"},
            {"id": "LONG_PUT", "name": "Long Put", "type": "Options - Put"},
            {"id": "BEAR_PUT_SPREAD", "name": "Bear Put Spread", "type": "Options - Put"},
            {"id": "PUT_RATIO_BACKSPREAD", "name": "Put Ratio Backspread", "type": "Options - Put"},
            {"id": "LONG_STRADDLE", "name": "Long Straddle", "type": "Options - Volatility"},
            {"id": "LONG_STRANGLE", "name": "Long Strangle", "type": "Options - Volatility"},
            {"id": "COVERED_CALL", "name": "Covered Call", "type": "Stock Options"},
            {"id": "COLLAR", "name": "Collar", "type": "Stock Options"},
            {"id": "DELTA_DIRECTIONAL", "name": "Delta Directional", "type": "Greeks"},
            {"id": "IV_EXPANSION_PLAY", "name": "IV Expansion Play", "type": "Greeks"},
            {"id": "OI_BREAKOUT", "name": "OI Breakout", "type": "Options Chain"},
        ]
    }
