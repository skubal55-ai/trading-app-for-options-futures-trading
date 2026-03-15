import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import logging
import requests
import json

logger = logging.getLogger(__name__)

NSE_SYMBOLS = {
    "NIFTY_50": "^NSEI",
    "NIFTY_BANK": "^NSEBANK",
    "NIFTY_IT": "^CNXIT",
    "NIFTY_FIN_SERVICE": "NIFTY_FIN_SERVICE.NS",
    "INDIA_VIX": "^INDIAVIX",
}

NIFTY50_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "BAJFINANCE",
    "HCLTECH", "WIPRO", "SUNPHARMA", "TATAMOTORS", "TITAN",
    "ULTRACEMCO", "NESTLEIND", "NTPC", "POWERGRID", "M&M",
    "JSWSTEEL", "TATASTEEL", "TECHM", "ADANIENT", "ADANIPORTS",
    "ONGC", "COALINDIA", "BAJAJFINSV", "GRASIM", "CIPLA",
    "DRREDDY", "EICHERMOT", "DIVISLAB", "BPCL", "BRITANNIA",
    "HEROMOTOCO", "APOLLOHOSP", "TATACONSUM", "SBILIFE", "HDFCLIFE",
    "INDUSINDBK", "UPL", "HINDALCO", "BAJAJ-AUTO", "LTIM",
]

INDEX_OPTIONS = ["NIFTY", "BANKNIFTY", "FINNIFTY"]


def get_nse_symbol(symbol: str) -> str:
    if symbol in NSE_SYMBOLS:
        return NSE_SYMBOLS[symbol]
    if not symbol.endswith(".NS") and not symbol.startswith("^"):
        return f"{symbol}.NS"
    return symbol


def get_stock_data(symbol: str, period: str = "1d", interval: str = "5m") -> Optional[pd.DataFrame]:
    try:
        nse_symbol = get_nse_symbol(symbol)
        ticker = yf.Ticker(nse_symbol)
        data = ticker.history(period=period, interval=interval)
        if data.empty:
            return None
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None


def get_stock_quote(symbol: str) -> Optional[dict]:
    try:
        nse_symbol = get_nse_symbol(symbol)
        ticker = yf.Ticker(nse_symbol)
        info = ticker.info
        hist = ticker.history(period="2d")

        if hist.empty:
            return None

        current = hist.iloc[-1]
        prev_close = hist.iloc[-2]["Close"] if len(hist) > 1 else current["Open"]

        ltp = float(current["Close"])
        change = ltp - float(prev_close)
        change_pct = (change / float(prev_close)) * 100 if prev_close != 0 else 0

        return {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "ltp": round(ltp, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "open": round(float(current["Open"]), 2),
            "high": round(float(current["High"]), 2),
            "low": round(float(current["Low"]), 2),
            "close": round(float(prev_close), 2),
            "volume": int(current["Volume"]),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        return None


def get_historical_data(symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    try:
        nse_symbol = get_nse_symbol(symbol)
        ticker = yf.Ticker(nse_symbol)
        data = ticker.history(period=period, interval=interval)
        if data.empty:
            return None
        return data
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        return None


def get_market_overview() -> dict:
    overview = {
        "market_status": "OPEN" if is_market_open() else "CLOSED",
        "top_gainers": [],
        "top_losers": [],
        "most_active": [],
    }

    for index_name, yahoo_symbol in [("NIFTY_50", "^NSEI"), ("NIFTY_BANK", "^NSEBANK")]:
        try:
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period="2d")
            if not hist.empty:
                current = hist.iloc[-1]
                prev_close = hist.iloc[-2]["Close"] if len(hist) > 1 else current["Open"]
                ltp = float(current["Close"])
                change = ltp - float(prev_close)
                change_pct = (change / float(prev_close)) * 100

                quote = {
                    "symbol": index_name.replace("_", " "),
                    "name": index_name.replace("_", " "),
                    "ltp": round(ltp, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2),
                    "open": round(float(current["Open"]), 2),
                    "high": round(float(current["High"]), 2),
                    "low": round(float(current["Low"]), 2),
                    "close": round(float(prev_close), 2),
                    "volume": int(current.get("Volume", 0)),
                    "timestamp": datetime.now().isoformat(),
                }
                if index_name == "NIFTY_50":
                    overview["nifty50"] = quote
                elif index_name == "NIFTY_BANK":
                    overview["nifty_bank"] = quote
        except Exception as e:
            logger.error(f"Error fetching {index_name}: {e}")

    try:
        vix_ticker = yf.Ticker("^INDIAVIX")
        vix_hist = vix_ticker.history(period="1d")
        if not vix_hist.empty:
            overview["india_vix"] = round(float(vix_hist.iloc[-1]["Close"]), 2)
    except Exception:
        pass

    stock_data = []
    for symbol in NIFTY50_STOCKS[:20]:
        quote = get_stock_quote(symbol)
        if quote:
            stock_data.append(quote)

    stock_data_sorted = sorted(stock_data, key=lambda x: x["change_percent"], reverse=True)
    overview["top_gainers"] = stock_data_sorted[:5]
    overview["top_losers"] = stock_data_sorted[-5:][::-1]
    overview["most_active"] = sorted(stock_data, key=lambda x: x["volume"], reverse=True)[:5]

    return overview


def get_option_chain(symbol: str) -> list[dict]:
    try:
        nse_symbol = get_nse_symbol(symbol)
        ticker = yf.Ticker(nse_symbol)
        expirations = ticker.options

        if not expirations:
            return []

        nearest_expiry = expirations[0]
        chain = ticker.option_chain(nearest_expiry)

        results = []
        calls = chain.calls
        puts = chain.puts

        for _, call_row in calls.iterrows():
            strike = float(call_row["strike"])
            put_row = puts[puts["strike"] == strike]

            entry = {
                "strike_price": strike,
                "expiry": nearest_expiry,
                "call_oi": int(call_row.get("openInterest", 0)),
                "call_change_oi": int(call_row.get("openInterest", 0)),
                "call_ltp": round(float(call_row.get("lastPrice", 0)), 2),
                "call_volume": int(call_row.get("volume", 0)),
                "call_iv": round(float(call_row.get("impliedVolatility", 0)) * 100, 2) if call_row.get("impliedVolatility") else None,
                "put_oi": 0,
                "put_change_oi": 0,
                "put_ltp": 0,
                "put_volume": 0,
                "put_iv": None,
            }

            if not put_row.empty:
                put_data = put_row.iloc[0]
                entry["put_oi"] = int(put_data.get("openInterest", 0))
                entry["put_change_oi"] = int(put_data.get("openInterest", 0))
                entry["put_ltp"] = round(float(put_data.get("lastPrice", 0)), 2)
                entry["put_volume"] = int(put_data.get("volume", 0))
                entry["put_iv"] = round(float(put_data.get("impliedVolatility", 0)) * 100, 2) if put_data.get("impliedVolatility") else None

            results.append(entry)

        return results
    except Exception as e:
        logger.error(f"Error fetching option chain for {symbol}: {e}")
        return []


def is_market_open() -> bool:
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def get_all_nifty50_quotes() -> list[dict]:
    quotes = []
    for symbol in NIFTY50_STOCKS:
        quote = get_stock_quote(symbol)
        if quote:
            quotes.append(quote)
    return quotes
