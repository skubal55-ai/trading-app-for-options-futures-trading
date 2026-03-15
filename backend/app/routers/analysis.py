from fastapi import APIRouter, Query
from typing import Optional
from app.services.nse_data import get_historical_data, get_stock_data, NIFTY50_STOCKS
from app.services.technical_analysis import (
    calculate_indicators,
    calculate_fibonacci_levels,
    calculate_pivot_points,
)

router = APIRouter(prefix="/api/analysis", tags=["Technical Analysis"])


@router.get("/indicators/{symbol}")
async def get_indicators(
    symbol: str,
    period: str = Query(default="3mo", description="Period for analysis"),
    interval: str = Query(default="1d", description="Data interval"),
):
    data = get_historical_data(symbol.upper(), period=period, interval=interval)
    if data is None:
        return {"error": f"Could not fetch data for {symbol}"}

    indicators = calculate_indicators(data)
    indicators["symbol"] = symbol.upper()
    return indicators


@router.get("/fibonacci/{symbol}")
async def get_fibonacci(
    symbol: str,
    period: str = Query(default="6mo", description="Period for Fibonacci calculation"),
):
    data = get_historical_data(symbol.upper(), period=period)
    if data is None:
        return {"error": f"Could not fetch data for {symbol}"}

    levels = calculate_fibonacci_levels(data)
    levels["symbol"] = symbol.upper()
    return levels


@router.get("/pivot-points/{symbol}")
async def get_pivot_points(symbol: str):
    data = get_historical_data(symbol.upper(), period="5d", interval="1d")
    if data is None:
        return {"error": f"Could not fetch data for {symbol}"}

    pivots = calculate_pivot_points(data)
    pivots["symbol"] = symbol.upper()
    return pivots


@router.get("/chart-data/{symbol}")
async def get_chart_data(
    symbol: str,
    period: str = Query(default="3mo"),
    interval: str = Query(default="1d"),
):
    data = get_historical_data(symbol.upper(), period=period, interval=interval)
    if data is None:
        return {"error": f"Could not fetch data for {symbol}"}

    indicators = calculate_indicators(data)
    fib = calculate_fibonacci_levels(data)
    pivots = calculate_pivot_points(data)

    chart_data = []
    close_series = data["Close"]

    sma_20 = close_series.rolling(window=20).mean() if len(close_series) >= 20 else None
    sma_50 = close_series.rolling(window=50).mean() if len(close_series) >= 50 else None
    ema_9 = close_series.ewm(span=9).mean() if len(close_series) >= 9 else None
    ema_21 = close_series.ewm(span=21).mean() if len(close_series) >= 21 else None

    for i, (idx, row) in enumerate(data.iterrows()):
        point = {
            "date": idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        }
        if sma_20 is not None and i >= 19:
            point["sma_20"] = round(float(sma_20.iloc[i]), 2)
        if sma_50 is not None and i >= 49:
            point["sma_50"] = round(float(sma_50.iloc[i]), 2)
        if ema_9 is not None and i >= 8:
            point["ema_9"] = round(float(ema_9.iloc[i]), 2)
        if ema_21 is not None and i >= 20:
            point["ema_21"] = round(float(ema_21.iloc[i]), 2)

        chart_data.append(point)

    return {
        "symbol": symbol.upper(),
        "chart_data": chart_data,
        "indicators": indicators,
        "fibonacci": fib,
        "pivot_points": pivots,
    }
