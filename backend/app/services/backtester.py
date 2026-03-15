"""
Backtesting Engine - Runs trading strategies against historical price data
to generate simulated trade results with P&L analysis.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

NIFTY50_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "BAJFINANCE",
    "HCLTECH", "WIPRO", "SUNPHARMA", "TATAMOTORS", "TITAN",
    "ULTRACEMCO", "NESTLEIND", "NTPC", "POWERGRID",
    "JSWSTEEL", "TATASTEEL", "TECHM", "ADANIENT", "ADANIPORTS",
    "ONGC", "COALINDIA", "BAJAJFINSV", "GRASIM", "CIPLA",
    "DRREDDY", "EICHERMOT", "DIVISLAB", "BPCL", "BRITANNIA",
    "HEROMOTOCO", "APOLLOHOSP", "TATACONSUM", "SBILIFE", "HDFCLIFE",
    "INDUSINDBK", "HINDALCO", "BAJAJ-AUTO", "LTIM",
]


def _get_nse_symbol(symbol: str) -> str:
    if not symbol.endswith(".NS") and not symbol.startswith("^"):
        return f"{symbol}.NS"
    return symbol


def _calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators used by strategies."""
    df = df.copy()
    # EMAs
    df["ema9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["ema21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["sma50"] = df["Close"].rolling(window=50).mean()
    df["sma200"] = df["Close"].rolling(window=200).mean()

    # RSI
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # Bollinger Bands
    df["bb_mid"] = df["Close"].rolling(window=20).mean()
    bb_std = df["Close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * bb_std
    df["bb_lower"] = df["bb_mid"] - 2 * bb_std

    # ATR
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()

    # Volume MA
    df["vol_ma20"] = df["Volume"].rolling(window=20).mean()

    # Supertrend (simplified)
    hl2 = (df["High"] + df["Low"]) / 2
    df["st_upper"] = hl2 + 2 * df["atr"]
    df["st_lower"] = hl2 - 2 * df["atr"]

    # ADX (simplified using directional movement)
    plus_dm = df["High"].diff()
    minus_dm = -df["Low"].diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    plus_di = 100 * (plus_dm.rolling(14).mean() / tr.rolling(14).mean())
    minus_di = 100 * (minus_dm.rolling(14).mean() / tr.rolling(14).mean())
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    df["adx"] = dx.rolling(14).mean()

    return df


def _generate_signals(df: pd.DataFrame, strategy: str) -> list[dict]:
    """Generate buy/sell signals based on strategy using historical data."""
    signals = []
    if len(df) < 60:
        return signals

    for i in range(55, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        close = float(row["Close"])
        atr = float(row["atr"]) if not pd.isna(row["atr"]) else close * 0.02
        date_str = str(row.name)

        signal = None
        strategy_name = strategy
        reason = ""
        confidence = 0.0

        if strategy == "MA_CROSSOVER":
            if (not pd.isna(row["ema9"]) and not pd.isna(row["ema21"])
                    and not pd.isna(prev["ema9"]) and not pd.isna(prev["ema21"])):
                if prev["ema9"] <= prev["ema21"] and row["ema9"] > row["ema21"]:
                    signal = "BUY"
                    reason = f"EMA 9 crossed above EMA 21"
                    confidence = 0.70
                    if not pd.isna(row["sma50"]) and close > row["sma50"]:
                        confidence = 0.80
                elif prev["ema9"] >= prev["ema21"] and row["ema9"] < row["ema21"]:
                    signal = "SELL"
                    reason = f"EMA 9 crossed below EMA 21"
                    confidence = 0.70

        elif strategy == "RSI_DIVERGENCE":
            if not pd.isna(row["rsi"]):
                if row["rsi"] < 30:
                    signal = "BUY"
                    reason = f"RSI oversold at {row['rsi']:.1f}"
                    confidence = 0.65 + (30 - row["rsi"]) / 100
                elif row["rsi"] > 70:
                    signal = "SELL"
                    reason = f"RSI overbought at {row['rsi']:.1f}"
                    confidence = 0.65 + (row["rsi"] - 70) / 100

        elif strategy == "MACD_SIGNAL":
            if (not pd.isna(row["macd"]) and not pd.isna(row["macd_signal"])
                    and not pd.isna(prev["macd"]) and not pd.isna(prev["macd_signal"])):
                if prev["macd"] <= prev["macd_signal"] and row["macd"] > row["macd_signal"]:
                    signal = "BUY"
                    reason = "MACD bullish crossover"
                    confidence = 0.72
                elif prev["macd"] >= prev["macd_signal"] and row["macd"] < row["macd_signal"]:
                    signal = "SELL"
                    reason = "MACD bearish crossover"
                    confidence = 0.72

        elif strategy == "BOLLINGER_BREAKOUT":
            if not pd.isna(row["bb_lower"]) and not pd.isna(row["bb_upper"]):
                if close <= row["bb_lower"]:
                    signal = "BUY"
                    reason = "Price at lower Bollinger Band"
                    confidence = 0.68
                elif close >= row["bb_upper"]:
                    signal = "SELL"
                    reason = "Price at upper Bollinger Band"
                    confidence = 0.68

        elif strategy == "SUPERTREND":
            if not pd.isna(row["st_lower"]) and not pd.isna(prev["st_lower"]):
                if close > row["st_upper"] and float(prev["Close"]) <= prev["st_upper"]:
                    signal = "BUY"
                    reason = "Price broke above Supertrend"
                    confidence = 0.73
                elif close < row["st_lower"] and float(prev["Close"]) >= prev["st_lower"]:
                    signal = "SELL"
                    reason = "Price broke below Supertrend"
                    confidence = 0.73

        elif strategy == "VOLUME_BREAKOUT":
            if not pd.isna(row["vol_ma20"]) and row["vol_ma20"] > 0:
                vol_ratio = float(row["Volume"]) / float(row["vol_ma20"])
                if vol_ratio > 2.0 and close > float(prev["Close"]):
                    signal = "BUY"
                    reason = f"Volume breakout {vol_ratio:.1f}x avg with price up"
                    confidence = 0.70 + min(vol_ratio - 2, 3) * 0.05
                elif vol_ratio > 2.0 and close < float(prev["Close"]):
                    signal = "SELL"
                    reason = f"Volume breakdown {vol_ratio:.1f}x avg with price down"
                    confidence = 0.70 + min(vol_ratio - 2, 3) * 0.05

        elif strategy == "EMA_RIBBON":
            ema8 = df["Close"].ewm(span=8, adjust=False).mean().iloc[i]
            ema13 = df["Close"].ewm(span=13, adjust=False).mean().iloc[i]
            ema34 = df["Close"].ewm(span=34, adjust=False).mean().iloc[i]
            ema55 = df["Close"].ewm(span=55, adjust=False).mean().iloc[i]
            if (not pd.isna(ema8) and not pd.isna(ema55)):
                if ema8 > ema13 > ema21 > ema34 > ema55:
                    prev_ema8 = df["Close"].ewm(span=8, adjust=False).mean().iloc[i - 1]
                    prev_ema13 = df["Close"].ewm(span=13, adjust=False).mean().iloc[i - 1]
                    if not (prev_ema8 > prev_ema13):
                        signal = "BUY"
                        reason = "EMA ribbon fully aligned bullish"
                        confidence = 0.78
                elif ema8 < ema13 < row["ema21"] < ema34 < ema55:
                    signal = "SELL"
                    reason = "EMA ribbon fully aligned bearish"
                    confidence = 0.78

        elif strategy in ("LONG_CALL", "BULL_CALL_SPREAD", "CALL_RATIO_BACKSPREAD"):
            if not pd.isna(row["rsi"]) and not pd.isna(row["macd"]):
                if (row["ema9"] > row["ema21"] and row["rsi"] > 50 and row["rsi"] < 70
                        and row["macd"] > row["macd_signal"]):
                    signal = "BUY"
                    reason = f"{strategy.replace('_', ' ').title()}: Bullish trend + MACD + RSI {row['rsi']:.0f}"
                    confidence = 0.72

        elif strategy in ("LONG_PUT", "BEAR_PUT_SPREAD", "PUT_RATIO_BACKSPREAD"):
            if not pd.isna(row["rsi"]) and not pd.isna(row["macd"]):
                if (row["ema9"] < row["ema21"] and row["rsi"] < 50 and row["rsi"] > 30
                        and row["macd"] < row["macd_signal"]):
                    signal = "SELL"
                    reason = f"{strategy.replace('_', ' ').title()}: Bearish trend + MACD + RSI {row['rsi']:.0f}"
                    confidence = 0.72

        elif strategy in ("LONG_STRADDLE", "LONG_STRANGLE"):
            if not pd.isna(row["bb_upper"]) and not pd.isna(row["bb_lower"]):
                bb_width = (row["bb_upper"] - row["bb_lower"]) / row["bb_mid"] * 100
                if not pd.isna(row["adx"]) and row["adx"] < 20 and bb_width < 4:
                    signal = "BUY"
                    reason = f"Volatility squeeze: ADX {row['adx']:.0f}, BB width {bb_width:.1f}%"
                    confidence = 0.68

        elif strategy in ("COVERED_CALL", "COLLAR"):
            if not pd.isna(row["rsi"]) and not pd.isna(row["adx"]):
                if row["adx"] < 25 and 40 < row["rsi"] < 60:
                    signal = "BUY"
                    reason = f"Range-bound: ADX {row['adx']:.0f}, RSI {row['rsi']:.0f} - sell premium"
                    confidence = 0.70

        elif strategy == "DELTA_DIRECTIONAL":
            if not pd.isna(row["adx"]) and row["adx"] > 25:
                if row["ema9"] > row["ema21"] and row["macd"] > 0:
                    signal = "BUY"
                    reason = f"Strong trend ADX {row['adx']:.0f}: buy high-delta call"
                    confidence = 0.75
                elif row["ema9"] < row["ema21"] and row["macd"] < 0:
                    signal = "SELL"
                    reason = f"Strong downtrend ADX {row['adx']:.0f}: buy high-delta put"
                    confidence = 0.75

        elif strategy == "IV_EXPANSION_PLAY":
            if not pd.isna(row["bb_upper"]) and not pd.isna(row["bb_lower"]):
                bb_width = (row["bb_upper"] - row["bb_lower"]) / row["bb_mid"] * 100
                if not pd.isna(row["adx"]) and row["adx"] < 18 and bb_width < 3.5:
                    signal = "BUY"
                    reason = f"IV low, BB squeeze {bb_width:.1f}%, ADX {row['adx']:.0f} - buy cheap options"
                    confidence = 0.66

        elif strategy == "OI_BREAKOUT":
            if not pd.isna(row["vol_ma20"]) and row["vol_ma20"] > 0:
                vol_ratio = float(row["Volume"]) / float(row["vol_ma20"])
                if vol_ratio > 1.8:
                    if close > float(prev["Close"]) * 1.01:
                        signal = "BUY"
                        reason = f"Volume {vol_ratio:.1f}x with breakout, options OI confirms"
                        confidence = 0.71
                    elif close < float(prev["Close"]) * 0.99:
                        signal = "SELL"
                        reason = f"Volume {vol_ratio:.1f}x with breakdown, options OI confirms"
                        confidence = 0.71

        if signal:
            if signal == "BUY":
                entry = close
                target = round(close + 2 * atr, 2)
                stop_loss = round(close - 1 * atr, 2)
            else:
                entry = close
                target = round(close - 2 * atr, 2)
                stop_loss = round(close + 1 * atr, 2)

            risk = abs(entry - stop_loss)
            reward = abs(target - entry)
            rr = round(reward / risk, 2) if risk > 0 else 2.0

            signals.append({
                "date": date_str,
                "signal": signal,
                "strategy": strategy_name,
                "entry_price": round(entry, 2),
                "target": target,
                "stop_loss": round(stop_loss, 2),
                "risk_reward": rr,
                "confidence": round(min(confidence, 0.95), 2),
                "reason": reason,
            })

    return signals


def _simulate_trades(df: pd.DataFrame, signals: list[dict], holding_days: int = 10) -> list[dict]:
    """Simulate trades by checking if target or stop-loss was hit."""
    trades = []
    date_index = df.index.tolist()
    date_str_map = {str(d): idx for idx, d in enumerate(date_index)}

    for sig in signals:
        sig_date = sig["date"]
        sig_idx = date_str_map.get(sig_date)
        if sig_idx is None:
            continue

        entry = sig["entry_price"]
        target = sig["target"]
        stop_loss = sig["stop_loss"]
        is_buy = sig["signal"] == "BUY"

        exit_price = entry
        exit_date = sig_date
        exit_reason = "EXPIRED"
        max_favorable = entry
        max_adverse = entry

        end_idx = min(sig_idx + holding_days, len(df) - 1)
        for j in range(sig_idx + 1, end_idx + 1):
            row = df.iloc[j]
            high = float(row["High"])
            low = float(row["Low"])
            close_j = float(row["Close"])

            if is_buy:
                max_favorable = max(max_favorable, high)
                max_adverse = min(max_adverse, low)
                if high >= target:
                    exit_price = target
                    exit_date = str(df.index[j])
                    exit_reason = "TARGET_HIT"
                    break
                elif low <= stop_loss:
                    exit_price = stop_loss
                    exit_date = str(df.index[j])
                    exit_reason = "STOP_LOSS_HIT"
                    break
            else:
                max_favorable = min(max_favorable, low)
                max_adverse = max(max_adverse, high)
                if low <= target:
                    exit_price = target
                    exit_date = str(df.index[j])
                    exit_reason = "TARGET_HIT"
                    break
                elif high >= stop_loss:
                    exit_price = stop_loss
                    exit_date = str(df.index[j])
                    exit_reason = "STOP_LOSS_HIT"
                    break

        if exit_reason == "EXPIRED":
            exit_price = float(df.iloc[end_idx]["Close"])
            exit_date = str(df.index[end_idx])

        if is_buy:
            pnl = exit_price - entry
            pnl_pct = (pnl / entry) * 100
            mfe = ((max_favorable - entry) / entry) * 100
            mae = ((entry - max_adverse) / entry) * 100
        else:
            pnl = entry - exit_price
            pnl_pct = (pnl / entry) * 100
            mfe = ((entry - max_favorable) / entry) * 100
            mae = ((max_adverse - entry) / entry) * 100

        entry_dt = sig_date.split(" ")[0] if " " in sig_date else sig_date[:10]
        exit_dt = exit_date.split(" ")[0] if " " in exit_date else exit_date[:10]

        trades.append({
            "entry_date": entry_dt,
            "exit_date": exit_dt,
            "signal": sig["signal"],
            "strategy": sig["strategy"],
            "entry_price": entry,
            "exit_price": round(exit_price, 2),
            "target": target,
            "stop_loss": stop_loss,
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_pct, 2),
            "exit_reason": exit_reason,
            "risk_reward": sig["risk_reward"],
            "confidence": sig["confidence"],
            "reason": sig["reason"],
            "max_favorable_excursion": round(mfe, 2),
            "max_adverse_excursion": round(mae, 2),
        })

    return trades


def _compute_stats(trades: list[dict]) -> dict:
    """Compute comprehensive backtest statistics."""
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "total_pnl_percent": 0,
            "avg_pnl_percent": 0,
            "avg_winner": 0,
            "avg_loser": 0,
            "max_winner": 0,
            "max_loser": 0,
            "profit_factor": 0,
            "expectancy": 0,
            "sharpe_estimate": 0,
            "max_drawdown": 0,
            "target_hit_rate": 0,
            "stop_loss_hit_rate": 0,
            "avg_holding_days": 0,
        }

    total = len(trades)
    winners = [t for t in trades if t["pnl"] > 0]
    losers = [t for t in trades if t["pnl"] <= 0]
    pnl_list = [t["pnl_percent"] for t in trades]

    total_pnl = sum(pnl_list)
    avg_pnl = total_pnl / total
    win_rate = len(winners) / total * 100

    avg_winner = np.mean([t["pnl_percent"] for t in winners]) if winners else 0
    avg_loser = np.mean([t["pnl_percent"] for t in losers]) if losers else 0
    max_winner = max([t["pnl_percent"] for t in trades])
    max_loser = min([t["pnl_percent"] for t in trades])

    gross_profit = sum(t["pnl_percent"] for t in winners)
    gross_loss = abs(sum(t["pnl_percent"] for t in losers))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    expectancy = (win_rate / 100 * avg_winner) + ((1 - win_rate / 100) * avg_loser)

    std_pnl = np.std(pnl_list) if len(pnl_list) > 1 else 1
    sharpe = (avg_pnl / std_pnl) * np.sqrt(252) if std_pnl > 0 else 0

    # Max drawdown on equity curve
    cumulative = np.cumsum(pnl_list)
    peak = np.maximum.accumulate(cumulative)
    drawdown = peak - cumulative
    max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0

    target_hits = sum(1 for t in trades if t["exit_reason"] == "TARGET_HIT")
    sl_hits = sum(1 for t in trades if t["exit_reason"] == "STOP_LOSS_HIT")

    # Approximate holding days
    avg_hold = 0
    try:
        hold_days_list = []
        for t in trades:
            d1 = datetime.strptime(t["entry_date"][:10], "%Y-%m-%d")
            d2 = datetime.strptime(t["exit_date"][:10], "%Y-%m-%d")
            hold_days_list.append((d2 - d1).days)
        avg_hold = np.mean(hold_days_list) if hold_days_list else 0
    except Exception:
        avg_hold = 0

    # Equity curve data
    equity_curve = []
    running = 0
    for t in trades:
        running += t["pnl_percent"]
        equity_curve.append({
            "date": t["exit_date"],
            "cumulative_pnl": round(running, 2),
            "symbol": t.get("symbol", ""),
        })

    return {
        "total_trades": total,
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": round(win_rate, 1),
        "total_pnl_percent": round(total_pnl, 2),
        "avg_pnl_percent": round(avg_pnl, 2),
        "avg_winner": round(float(avg_winner), 2),
        "avg_loser": round(float(avg_loser), 2),
        "max_winner": round(max_winner, 2),
        "max_loser": round(max_loser, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 99.0,
        "expectancy": round(expectancy, 2),
        "sharpe_estimate": round(float(sharpe), 2),
        "max_drawdown": round(max_dd, 2),
        "target_hit_rate": round(target_hits / total * 100, 1) if total > 0 else 0,
        "stop_loss_hit_rate": round(sl_hits / total * 100, 1) if total > 0 else 0,
        "avg_holding_days": round(float(avg_hold), 1),
        "equity_curve": equity_curve,
    }


def run_backtest(
    symbols: Optional[list[str]] = None,
    strategy: str = "MA_CROSSOVER",
    period: str = "1y",
    holding_days: int = 10,
    capital: float = 100000,
) -> dict:
    """
    Run backtest for given symbols and strategy.

    Args:
        symbols: List of stock symbols (defaults to top NIFTY50 stocks)
        strategy: Strategy name to backtest
        period: Historical period (e.g., '6mo', '1y', '2y')
        holding_days: Max days to hold a trade
        capital: Starting capital for P&L calculation

    Returns:
        Dict with trades, stats, and equity curve
    """
    if symbols is None:
        symbols = NIFTY50_STOCKS[:15]

    all_trades = []

    for symbol in symbols:
        try:
            nse_sym = _get_nse_symbol(symbol)
            ticker = yf.Ticker(nse_sym)
            df = ticker.history(period=period, interval="1d")

            if df is None or df.empty or len(df) < 60:
                continue

            df = _calculate_indicators(df)
            signals = _generate_signals(df, strategy)

            if not signals:
                continue

            trades = _simulate_trades(df, signals, holding_days)

            for t in trades:
                t["symbol"] = symbol
                # Calculate absolute P&L based on capital allocation
                allocation = capital / len(symbols)
                qty = int(allocation / t["entry_price"]) if t["entry_price"] > 0 else 0
                t["quantity"] = qty
                t["absolute_pnl"] = round(t["pnl"] * qty, 2)

            all_trades.extend(trades)

        except Exception as e:
            logger.error(f"Backtest error for {symbol}: {e}")
            continue

    # Sort by entry date
    all_trades.sort(key=lambda x: x["entry_date"])

    stats = _compute_stats(all_trades)

    # Compute portfolio equity curve
    portfolio_equity = []
    running_pnl = 0
    for t in all_trades:
        running_pnl += t["absolute_pnl"]
        portfolio_equity.append({
            "date": t["exit_date"],
            "equity": round(capital + running_pnl, 2),
            "cumulative_pnl": round(running_pnl, 2),
            "symbol": t["symbol"],
        })

    # Compute strategy-level summary
    strategy_perf = {}
    for t in all_trades:
        s = t["strategy"]
        if s not in strategy_perf:
            strategy_perf[s] = {"trades": 0, "wins": 0, "total_pnl": 0}
        strategy_perf[s]["trades"] += 1
        if t["pnl"] > 0:
            strategy_perf[s]["wins"] += 1
        strategy_perf[s]["total_pnl"] += t["pnl_percent"]

    strategy_summary = []
    for s, p in strategy_perf.items():
        strategy_summary.append({
            "strategy": s,
            "trades": p["trades"],
            "win_rate": round(p["wins"] / p["trades"] * 100, 1) if p["trades"] > 0 else 0,
            "total_pnl_pct": round(p["total_pnl"], 2),
        })

    # Per-symbol summary
    symbol_perf = {}
    for t in all_trades:
        s = t["symbol"]
        if s not in symbol_perf:
            symbol_perf[s] = {"trades": 0, "wins": 0, "total_pnl": 0, "absolute_pnl": 0}
        symbol_perf[s]["trades"] += 1
        if t["pnl"] > 0:
            symbol_perf[s]["wins"] += 1
        symbol_perf[s]["total_pnl"] += t["pnl_percent"]
        symbol_perf[s]["absolute_pnl"] += t["absolute_pnl"]

    symbol_summary = []
    for s, p in symbol_perf.items():
        symbol_summary.append({
            "symbol": s,
            "trades": p["trades"],
            "win_rate": round(p["wins"] / p["trades"] * 100, 1) if p["trades"] > 0 else 0,
            "total_pnl_pct": round(p["total_pnl"], 2),
            "absolute_pnl": round(p["absolute_pnl"], 2),
        })

    symbol_summary.sort(key=lambda x: x["total_pnl_pct"], reverse=True)

    # Filter top profitable trades for display
    profitable_trades = [t for t in all_trades if t["pnl"] > 0]
    profitable_trades.sort(key=lambda x: x["pnl_percent"], reverse=True)
    top_winners = profitable_trades[:20]

    return {
        "strategy": strategy,
        "period": period,
        "holding_days": holding_days,
        "capital": capital,
        "total_symbols_scanned": len(symbols),
        "stats": stats,
        "trades": all_trades,
        "top_winners": top_winners,
        "portfolio_equity": portfolio_equity,
        "strategy_summary": strategy_summary,
        "symbol_summary": symbol_summary,
    }
