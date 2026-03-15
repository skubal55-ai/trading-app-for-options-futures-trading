from fastapi import APIRouter, Query
from typing import Optional
from app.services.nse_data import (
    get_stock_quote,
    get_stock_data,
    get_historical_data,
    get_market_overview,
    get_option_chain,
    get_all_nifty50_quotes,
    NIFTY50_STOCKS,
    is_market_open,
)

router = APIRouter(prefix="/api/market", tags=["Market Data"])


@router.get("/overview")
async def market_overview():
    return get_market_overview()


@router.get("/quote/{symbol}")
async def stock_quote(symbol: str):
    quote = get_stock_quote(symbol.upper())
    if not quote:
        return {"error": f"Could not fetch data for {symbol}"}
    return quote


@router.get("/historical/{symbol}")
async def historical_data(
    symbol: str,
    period: str = Query(default="6mo", description="Period: 1d,5d,1mo,3mo,6mo,1y,2y,5y"),
    interval: str = Query(default="1d", description="Interval: 1m,5m,15m,1h,1d,1wk"),
):
    data = get_historical_data(symbol.upper(), period=period, interval=interval)
    if data is None:
        return {"error": f"Could not fetch historical data for {symbol}"}

    records = []
    for idx, row in data.iterrows():
        records.append({
            "date": idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })
    return {"symbol": symbol.upper(), "data": records}


@router.get("/intraday/{symbol}")
async def intraday_data(
    symbol: str,
    interval: str = Query(default="5m", description="Interval: 1m,5m,15m,30m,1h"),
):
    data = get_stock_data(symbol.upper(), period="1d", interval=interval)
    if data is None:
        return {"error": f"Could not fetch intraday data for {symbol}"}

    records = []
    for idx, row in data.iterrows():
        records.append({
            "date": idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })
    return {"symbol": symbol.upper(), "data": records}


@router.get("/option-chain/{symbol}")
async def option_chain(symbol: str):
    chain = get_option_chain(symbol.upper())
    if not chain:
        return {"error": f"Could not fetch option chain for {symbol}", "data": []}
    return {"symbol": symbol.upper(), "data": chain}


@router.get("/nifty50")
async def nifty50_stocks():
    return {"symbols": NIFTY50_STOCKS}


@router.get("/status")
async def market_status():
    return {"is_open": is_market_open()}


@router.get("/watchlist")
async def watchlist():
    quotes = []
    for symbol in NIFTY50_STOCKS[:10]:
        quote = get_stock_quote(symbol)
        if quote:
            quotes.append(quote)
    return {"data": quotes}
