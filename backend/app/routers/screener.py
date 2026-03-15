from fastapi import APIRouter, Query
from typing import Optional
from app.services.strategy_engine import run_screener, STRATEGY_ANALYZERS
from app.services.nse_data import NIFTY50_STOCKS

router = APIRouter(prefix="/api/screener", tags=["Screener"])


@router.get("/scan")
async def scan_stocks(
    strategies: Optional[str] = Query(default=None, description="Comma-separated strategy names"),
    signal: Optional[str] = Query(default=None, description="BUY or SELL filter"),
    symbols: Optional[str] = Query(default=None, description="Comma-separated symbols, defaults to NIFTY50"),
    limit: int = Query(default=20, description="Max results"),
):
    symbol_list = symbols.split(",") if symbols else NIFTY50_STOCKS[:15]
    strategy_list = strategies.split(",") if strategies else None

    results = run_screener(
        symbols=symbol_list,
        strategies=strategy_list,
        signal_filter=signal,
    )

    return {"results": results[:limit], "total": len(results)}


@router.get("/strategies")
async def available_strategies():
    return {
        "strategies": [
            {
                "id": "MA_CROSSOVER",
                "name": "Moving Average Crossover",
                "description": "EMA 9/21 crossover with SMA 50 trend confirmation",
                "type": "Trend Following",
            },
            {
                "id": "RSI_DIVERGENCE",
                "name": "RSI Divergence",
                "description": "RSI oversold/overbought signals with MACD confirmation",
                "type": "Mean Reversion",
            },
            {
                "id": "MACD_SIGNAL",
                "name": "MACD Signal",
                "description": "MACD line crossover with signal line confirmation",
                "type": "Momentum",
            },
            {
                "id": "FIBONACCI_RETRACEMENT",
                "name": "Fibonacci Retracement",
                "description": "Price action at key Fibonacci levels (38.2%, 50%, 61.8%)",
                "type": "Support/Resistance",
            },
            {
                "id": "BOLLINGER_BREAKOUT",
                "name": "Bollinger Band Breakout",
                "description": "Price touching or breaking Bollinger Bands for reversal signals",
                "type": "Volatility",
            },
            {
                "id": "SUPERTREND",
                "name": "Supertrend",
                "description": "Supertrend indicator for trend direction and entry points",
                "type": "Trend Following",
            },
            {
                "id": "VWAP_STRATEGY",
                "name": "VWAP Strategy",
                "description": "Volume Weighted Average Price for intraday support/resistance",
                "type": "Intraday",
            },
              {
                "id": "ORDER_BLOCK",
                "name": "Order Block (SMC)",
                "description": "Smart Money Concept - institutional order blocks with volume confirmation",
                "type": "Institutional",
            },
            {
                "id": "SUPPLY_DEMAND",
                "name": "Supply & Demand Zones",
                "description": "Identifies institutional accumulation and distribution zones",
                "type": "Institutional",
            },
            {
                "id": "EMA_RIBBON",
                "name": "EMA Ribbon",
                "description": "Multi-EMA (8,13,21,34,55) alignment for strong trend confirmation",
                "type": "Trend Following",
            },
            {
                "id": "VOLUME_BREAKOUT",
                "name": "Volume Breakout",
                "description": "Breakouts with 2x+ average volume - institutional participation",
                "type": "Breakout",
            },
            {
                "id": "ICT_FVG",
                "name": "ICT Fair Value Gap",
                "description": "Inner Circle Trader concept - price gaps indicating smart money activity",
                "type": "Smart Money",
            },
            {
                "id": "ORB_STRATEGY",
                "name": "Opening Range Breakout",
                "description": "15-minute opening range breakout/breakdown for intraday trading",
                "type": "Intraday",
            },
        ]
    }



@router.get("/quick-scan/{strategy}")
async def quick_scan(
    strategy: str,
    signal: Optional[str] = Query(default=None),
    limit: int = Query(default=10),
):
    results = run_screener(
        symbols=NIFTY50_STOCKS[:15],
        strategies=[strategy.upper()],
        signal_filter=signal,
    )
    return {"strategy": strategy.upper(), "results": results[:limit]}
