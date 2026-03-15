import pandas as pd
import numpy as np
from typing import Optional
from app.services.technical_analysis import (
    calculate_indicators,
    calculate_fibonacci_levels,
    calculate_pivot_points,
)
from app.services.nse_data import get_stock_data, get_historical_data, get_stock_quote
import logging

logger = logging.getLogger(__name__)


def analyze_ma_crossover(symbol: str) -> Optional[dict]:
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 50:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote or not indicators.get("ema_9") or not indicators.get("ema_21"):
            return None

        ema_9 = indicators["ema_9"]
        ema_21 = indicators["ema_21"]
        sma_50 = indicators.get("sma_50", 0)
        ltp = quote["ltp"]

        ema_9_prev = float(pd.Series(data["Close"]).ewm(span=9).mean().iloc[-2])
        ema_21_prev = float(pd.Series(data["Close"]).ewm(span=21).mean().iloc[-2])

        signal = None
        if ema_9 > ema_21 and ema_9_prev <= ema_21_prev:
            signal = "BUY"
        elif ema_9 < ema_21 and ema_9_prev >= ema_21_prev:
            signal = "SELL"

        if not signal:
            if ema_9 > ema_21 and ltp > sma_50:
                signal = "BUY"
                confidence = 0.6
            elif ema_9 < ema_21 and ltp < sma_50:
                signal = "SELL"
                confidence = 0.6
            else:
                return None
        else:
            confidence = 0.8

        atr = indicators.get("atr", ltp * 0.02)
        if signal == "BUY":
            stop_loss = round(ltp - 2 * atr, 2)
            target = round(ltp + 3 * atr, 2)
        else:
            stop_loss = round(ltp + 2 * atr, 2)
            target = round(ltp - 3 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "MA_CROSSOVER",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": f"EMA 9 ({ema_9}) {'crossed above' if signal == 'BUY' else 'crossed below'} EMA 21 ({ema_21})",
        }
    except Exception as e:
        logger.error(f"MA Crossover error for {symbol}: {e}")
        return None


def analyze_rsi_divergence(symbol: str) -> Optional[dict]:
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 30:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote or not indicators.get("rsi"):
            return None

        rsi = indicators["rsi"]
        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.02)

        signal = None
        confidence = 0.7
        reason = ""

        if rsi < 30:
            signal = "BUY"
            reason = f"RSI oversold at {rsi}"
            confidence = 0.75
        elif rsi > 70:
            signal = "SELL"
            reason = f"RSI overbought at {rsi}"
            confidence = 0.75
        elif rsi < 40 and indicators.get("macd_histogram", 0) > 0:
            signal = "BUY"
            reason = f"RSI recovering from {rsi} with positive MACD histogram"
            confidence = 0.65
        elif rsi > 60 and indicators.get("macd_histogram", 0) < 0:
            signal = "SELL"
            reason = f"RSI declining from {rsi} with negative MACD histogram"
            confidence = 0.65
        else:
            return None

        if signal == "BUY":
            stop_loss = round(ltp - 2 * atr, 2)
            target = round(ltp + 3 * atr, 2)
        else:
            stop_loss = round(ltp + 2 * atr, 2)
            target = round(ltp - 3 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "RSI_DIVERGENCE",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"RSI error for {symbol}: {e}")
        return None


def analyze_macd_signal(symbol: str) -> Optional[dict]:
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 30:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote or not indicators.get("macd"):
            return None

        macd = indicators["macd"]
        macd_signal_val = indicators["macd_signal"]
        histogram = indicators["macd_histogram"]
        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.02)

        import ta as ta_lib
        macd_line = ta_lib.trend.MACD(data["Close"]).macd()
        signal_line = ta_lib.trend.MACD(data["Close"]).macd_signal()

        prev_macd = float(macd_line.iloc[-2])
        prev_signal = float(signal_line.iloc[-2])

        signal = None
        confidence = 0.7
        reason = ""

        if macd > macd_signal_val and prev_macd <= prev_signal:
            signal = "BUY"
            reason = f"MACD bullish crossover (MACD: {macd}, Signal: {macd_signal_val})"
            confidence = 0.8
        elif macd < macd_signal_val and prev_macd >= prev_signal:
            signal = "SELL"
            reason = f"MACD bearish crossover (MACD: {macd}, Signal: {macd_signal_val})"
            confidence = 0.8
        elif histogram > 0 and macd > 0:
            signal = "BUY"
            reason = f"MACD bullish momentum (Histogram: {histogram})"
            confidence = 0.6
        elif histogram < 0 and macd < 0:
            signal = "SELL"
            reason = f"MACD bearish momentum (Histogram: {histogram})"
            confidence = 0.6
        else:
            return None

        if signal == "BUY":
            stop_loss = round(ltp - 2 * atr, 2)
            target = round(ltp + 3 * atr, 2)
        else:
            stop_loss = round(ltp + 2 * atr, 2)
            target = round(ltp - 3 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "MACD_SIGNAL",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"MACD error for {symbol}: {e}")
        return None


def analyze_fibonacci(symbol: str) -> Optional[dict]:
    try:
        data = get_historical_data(symbol, period="6mo", interval="1d")
        if data is None or len(data) < 30:
            return None

        fib = calculate_fibonacci_levels(data)
        quote = get_stock_quote(symbol)
        if not quote or not fib:
            return None

        ltp = quote["ltp"]
        indicators = calculate_indicators(data)
        atr = indicators.get("atr", ltp * 0.02)

        signal = None
        confidence = 0.65
        reason = ""

        tolerance = ltp * 0.01

        for level_name, level_val in [
            ("38.2%", fib["level_382"]),
            ("50%", fib["level_500"]),
            ("61.8%", fib["level_618"]),
        ]:
            if abs(ltp - level_val) < tolerance:
                if fib["trend"] == "UP":
                    signal = "BUY"
                    reason = f"Price at Fibonacci {level_name} support ({level_val}) in uptrend"
                    confidence = 0.7
                else:
                    signal = "SELL"
                    reason = f"Price at Fibonacci {level_name} resistance ({level_val}) in downtrend"
                    confidence = 0.7
                break

        if not signal:
            return None

        if signal == "BUY":
            stop_loss = round(ltp - 2 * atr, 2)
            target = round(ltp + 3 * atr, 2)
        else:
            stop_loss = round(ltp + 2 * atr, 2)
            target = round(ltp - 3 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "FIBONACCI_RETRACEMENT",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"Fibonacci error for {symbol}: {e}")
        return None


def analyze_bollinger_breakout(symbol: str) -> Optional[dict]:
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 20:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote or not indicators.get("bollinger_upper"):
            return None

        ltp = quote["ltp"]
        upper = indicators["bollinger_upper"]
        lower = indicators["bollinger_lower"]
        middle = indicators["bollinger_middle"]
        atr = indicators.get("atr", ltp * 0.02)

        signal = None
        confidence = 0.65
        reason = ""

        if ltp <= lower:
            signal = "BUY"
            reason = f"Price touching lower Bollinger Band ({lower}), potential reversal"
            confidence = 0.7
        elif ltp >= upper:
            signal = "SELL"
            reason = f"Price touching upper Bollinger Band ({upper}), potential reversal"
            confidence = 0.7
        else:
            return None

        if signal == "BUY":
            stop_loss = round(lower - atr, 2)
            target = round(middle + (middle - lower) * 0.5, 2)
        else:
            stop_loss = round(upper + atr, 2)
            target = round(middle - (upper - middle) * 0.5, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "BOLLINGER_BREAKOUT",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"Bollinger error for {symbol}: {e}")
        return None


def analyze_supertrend(symbol: str) -> Optional[dict]:
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 20:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote or not indicators.get("supertrend"):
            return None

        ltp = quote["ltp"]
        st = indicators["supertrend"]
        direction = indicators["supertrend_direction"]
        atr = indicators.get("atr", ltp * 0.02)

        signal = None
        confidence = 0.7
        reason = ""

        if direction == "UP":
            signal = "BUY"
            reason = f"Supertrend bullish ({st}), price above trend"
            confidence = 0.72
        else:
            signal = "SELL"
            reason = f"Supertrend bearish ({st}), price below trend"
            confidence = 0.72

        if signal == "BUY":
            stop_loss = round(st - atr * 0.5, 2)
            target = round(ltp + 3 * atr, 2)
        else:
            stop_loss = round(st + atr * 0.5, 2)
            target = round(ltp - 3 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "SUPERTREND",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"Supertrend error for {symbol}: {e}")
        return None


def analyze_vwap(symbol: str) -> Optional[dict]:
    try:
        data = get_stock_data(symbol, period="1d", interval="5m")
        if data is None or len(data) < 10:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote or not indicators.get("vwap"):
            return None

        ltp = quote["ltp"]
        vwap = indicators["vwap"]
        atr = indicators.get("atr", ltp * 0.005)

        signal = None
        confidence = 0.65
        reason = ""

        if ltp > vwap and ltp < vwap * 1.005:
            signal = "BUY"
            reason = f"Price bouncing off VWAP support ({vwap})"
            confidence = 0.68
        elif ltp < vwap and ltp > vwap * 0.995:
            signal = "SELL"
            reason = f"Price rejected at VWAP resistance ({vwap})"
            confidence = 0.68
        else:
            return None

        if signal == "BUY":
            stop_loss = round(vwap - 2 * atr, 2)
            target = round(ltp + 3 * atr, 2)
        else:
            stop_loss = round(vwap + 2 * atr, 2)
            target = round(ltp - 3 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "VWAP_STRATEGY",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"VWAP error for {symbol}: {e}")
        return None


STRATEGY_ANALYZERS = {
    "MA_CROSSOVER": analyze_ma_crossover,
    "RSI_DIVERGENCE": analyze_rsi_divergence,
    "MACD_SIGNAL": analyze_macd_signal,
    "FIBONACCI_RETRACEMENT": analyze_fibonacci,
    "BOLLINGER_BREAKOUT": analyze_bollinger_breakout,
    "SUPERTREND": analyze_supertrend,
    "VWAP_STRATEGY": analyze_vwap,
}


def run_screener(
    symbols: list[str],
    strategies: list[str] | None = None,
    signal_filter: str | None = None,
) -> list[dict]:
    if strategies is None:
        strategies = list(STRATEGY_ANALYZERS.keys())

    results = []
    for symbol in symbols:
        for strategy_name in strategies:
            analyzer = STRATEGY_ANALYZERS.get(strategy_name)
            if not analyzer:
                continue
            result = analyzer(symbol)
            if result:
                if signal_filter and result["signal"] != signal_filter:
                    continue
                results.append(result)

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results
