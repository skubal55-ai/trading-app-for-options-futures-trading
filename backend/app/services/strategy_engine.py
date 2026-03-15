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

def analyze_order_block(symbol: str) -> Optional[dict]:
    """Order Block / Smart Money Concept (SMC) strategy used by institutional traders."""
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 30:
            return None
        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None
        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.02)
        closes = data["Close"].values
        highs = data["High"].values
        lows = data["Low"].values
        volumes = data["Volume"].values
        signal = None
        confidence = 0.7
        reason = ""
        # Detect bullish order block: large bearish candle followed by strong bullish move
        for i in range(len(closes) - 5, len(closes) - 1):
            if i < 1:
                continue
            # Bearish candle with high volume followed by bullish breakout
            if closes[i] < closes[i - 1] and volumes[i] > np.mean(volumes[-20:]) * 1.5:
                # Check if price came back to this zone
                ob_high = float(highs[i])
                ob_low = float(lows[i])
                if ob_low <= ltp <= ob_high * 1.01:
                    signal = "BUY"
                    reason = f"Bullish Order Block at ₹{ob_low:.0f}-₹{ob_high:.0f} zone with institutional volume"
                    confidence = 0.75
                    break
        # Detect bearish order block
        if not signal:
            for i in range(len(closes) - 5, len(closes) - 1):
                if i < 1:
                    continue
                if closes[i] > closes[i - 1] and volumes[i] > np.mean(volumes[-20:]) * 1.5:
                    ob_high = float(highs[i])
                    ob_low = float(lows[i])
                    if ob_low * 0.99 <= ltp <= ob_high:
                        signal = "SELL"
                        reason = f"Bearish Order Block at ₹{ob_low:.0f}-₹{ob_high:.0f} zone with institutional volume"
                        confidence = 0.75
                        break
        if not signal:
            return None
        if signal == "BUY":
            stop_loss = round(ltp - 2.5 * atr, 2)
            target = round(ltp + 4 * atr, 2)
        else:
            stop_loss = round(ltp + 2.5 * atr, 2)
            target = round(ltp - 4 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0
        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "ORDER_BLOCK",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"Order Block error for {symbol}: {e}")
        return None
def analyze_supply_demand(symbol: str) -> Optional[dict]:
    """Supply and Demand Zone strategy - identifies institutional buying/selling zones."""
    try:
        data = get_historical_data(symbol, period="6mo", interval="1d")
        if data is None or len(data) < 40:
            return None
        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None
        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.02)
        closes = data["Close"].values
        highs = data["High"].values
        lows = data["Low"].values
        signal = None
        confidence = 0.68
        reason = ""
        # Find demand zones (strong rally bases)
        for i in range(5, len(closes) - 2):
            # Consolidation followed by strong up move
            range_size = float(highs[i] - lows[i])
            avg_range = float(np.mean(highs[i-5:i] - lows[i-5:i]))
            next_move = float(closes[i + 1] - closes[i])
            if range_size < avg_range * 0.6 and next_move > avg_range * 1.5:
                zone_low = float(lows[i])
                zone_high = float(highs[i])
                if zone_low * 0.99 <= ltp <= zone_high * 1.01:
                    signal = "BUY"
                    reason = f"Demand Zone at ₹{zone_low:.0f}-₹{zone_high:.0f}, institutional accumulation area"
                    confidence = 0.72
                    break
        # Find supply zones (strong drop bases)
        if not signal:
            for i in range(5, len(closes) - 2):
                range_size = float(highs[i] - lows[i])
                avg_range = float(np.mean(highs[i-5:i] - lows[i-5:i]))
                next_move = float(closes[i] - closes[i + 1])
                if range_size < avg_range * 0.6 and next_move > avg_range * 1.5:
                    zone_low = float(lows[i])
                    zone_high = float(highs[i])
                    if zone_low * 0.99 <= ltp <= zone_high * 1.01:
                        signal = "SELL"
                        reason = f"Supply Zone at ₹{zone_low:.0f}-₹{zone_high:.0f}, institutional distribution area"
                        confidence = 0.72
                        break
        if not signal:
            return None
        if signal == "BUY":
            stop_loss = round(ltp - 2 * atr, 2)
            target = round(ltp + 3.5 * atr, 2)
        else:
            stop_loss = round(ltp + 2 * atr, 2)
            target = round(ltp - 3.5 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0
        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "SUPPLY_DEMAND",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"Supply/Demand error for {symbol}: {e}")
        return None
def analyze_ema_ribbon(symbol: str) -> Optional[dict]:
    """EMA Ribbon strategy - uses multiple EMAs (8,13,21,34,55) for trend strength."""
    try:
        data = get_historical_data(symbol, period="6mo", interval="1d")
        if data is None or len(data) < 60:
            return None
        quote = get_stock_quote(symbol)
        indicators = calculate_indicators(data)
        if not quote:
            return None
        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.02)
        close_series = pd.Series(data["Close"])
        ema_8 = float(close_series.ewm(span=8).mean().iloc[-1])
        ema_13 = float(close_series.ewm(span=13).mean().iloc[-1])
        ema_21 = float(close_series.ewm(span=21).mean().iloc[-1])
        ema_34 = float(close_series.ewm(span=34).mean().iloc[-1])
        ema_55 = float(close_series.ewm(span=55).mean().iloc[-1])
        signal = None
        confidence = 0.7
        reason = ""
        # Bullish ribbon: all EMAs aligned upward
        if ema_8 > ema_13 > ema_21 > ema_34 > ema_55 and ltp > ema_8:
            signal = "BUY"
            reason = f"Bullish EMA Ribbon - all EMAs (8,13,21,34,55) aligned upward, strong trend"
            confidence = 0.78
        # Bearish ribbon: all EMAs aligned downward
        elif ema_8 < ema_13 < ema_21 < ema_34 < ema_55 and ltp < ema_8:
            signal = "SELL"
            reason = f"Bearish EMA Ribbon - all EMAs (8,13,21,34,55) aligned downward, strong downtrend"
            confidence = 0.78
        # Bullish ribbon expansion (price crossing above ribbon)
        elif ltp > ema_8 > ema_13 and ema_21 > ema_34:
            signal = "BUY"
            reason = f"EMA Ribbon expansion - price above EMA 8 ({ema_8:.0f}), bullish momentum building"
            confidence = 0.65
        if not signal:
            return None
        if signal == "BUY":
            stop_loss = round(ema_21 - atr, 2)
            target = round(ltp + 3 * atr, 2)
        else:
            stop_loss = round(ema_21 + atr, 2)
            target = round(ltp - 3 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0
        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "EMA_RIBBON",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"EMA Ribbon error for {symbol}: {e}")
        return None
def analyze_volume_breakout(symbol: str) -> Optional[dict]:
    """Volume Breakout strategy - detects breakouts with unusual volume (used by institutional traders)."""
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 30:
            return None
        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None
        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.02)
        closes = data["Close"].values
        highs = data["High"].values
        volumes = data["Volume"].values
        avg_volume = float(np.mean(volumes[-20:]))
        latest_volume = float(volumes[-1])
        volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0
        # 20-day high/low
        high_20 = float(np.max(highs[-20:]))
        low_20 = float(np.min(data["Low"].values[-20:]))
        signal = None
        confidence = 0.7
        reason = ""
        # Bullish volume breakout: price near 20-day high with 2x+ volume
        if volume_ratio >= 2.0 and ltp >= high_20 * 0.98:
            signal = "BUY"
            reason = f"Volume Breakout - {volume_ratio:.1f}x avg volume near 20-day high (₹{high_20:.0f})"
            confidence = 0.76
        # Bearish volume breakdown
        elif volume_ratio >= 2.0 and ltp <= low_20 * 1.02:
            signal = "SELL"
            reason = f"Volume Breakdown - {volume_ratio:.1f}x avg volume near 20-day low (₹{low_20:.0f})"
            confidence = 0.76
        # Moderate volume with price action
        elif volume_ratio >= 1.5:
            if closes[-1] > closes[-2] and closes[-2] > closes[-3]:
                signal = "BUY"
                reason = f"Rising price with {volume_ratio:.1f}x volume, momentum building"
                confidence = 0.62
            elif closes[-1] < closes[-2] and closes[-2] < closes[-3]:
                signal = "SELL"
                reason = f"Falling price with {volume_ratio:.1f}x volume, selling pressure"
                confidence = 0.62
        if not signal:
            return None
        if signal == "BUY":
            stop_loss = round(ltp - 2 * atr, 2)
            target = round(ltp + 3.5 * atr, 2)
        else:
            stop_loss = round(ltp + 2 * atr, 2)
            target = round(ltp - 3.5 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0
        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "VOLUME_BREAKOUT",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"Volume Breakout error for {symbol}: {e}")
        return None
def analyze_ict_fair_value_gap(symbol: str) -> Optional[dict]:
    """ICT Fair Value Gap (FVG) - Inner Circle Trader concept used by smart money."""
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 20:
            return None
        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None
        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.02)
        highs = data["High"].values
        lows = data["Low"].values
        closes = data["Close"].values
        signal = None
        confidence = 0.7
        reason = ""
        # Look for bullish FVG: gap between candle 1 high and candle 3 low
        for i in range(len(closes) - 5, len(closes) - 1):
            if i < 2:
                continue
            # Bullish FVG
            if float(lows[i + 1]) > float(highs[i - 1]):
                fvg_low = float(highs[i - 1])
                fvg_high = float(lows[i + 1]) if i + 1 < len(lows) else float(lows[i])
                if fvg_low * 0.99 <= ltp <= fvg_high * 1.01:
                    signal = "BUY"
                    reason = f"ICT Bullish Fair Value Gap at ₹{fvg_low:.0f}-₹{fvg_high:.0f}, smart money zone"
                    confidence = 0.73
                    break
            # Bearish FVG
            if float(highs[i + 1]) < float(lows[i - 1]):
                fvg_high = float(lows[i - 1])
                fvg_low = float(highs[i + 1]) if i + 1 < len(highs) else float(highs[i])
                if fvg_low * 0.99 <= ltp <= fvg_high * 1.01:
                    signal = "SELL"
                    reason = f"ICT Bearish Fair Value Gap at ₹{fvg_low:.0f}-₹{fvg_high:.0f}, smart money zone"
                    confidence = 0.73
                    break
        if not signal:
            return None
        if signal == "BUY":
            stop_loss = round(ltp - 2 * atr, 2)
            target = round(ltp + 3.5 * atr, 2)
        else:
            stop_loss = round(ltp + 2 * atr, 2)
            target = round(ltp - 3.5 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0
        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "ICT_FVG",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"ICT FVG error for {symbol}: {e}")
        return None
def analyze_opening_range_breakout(symbol: str) -> Optional[dict]:
    """Opening Range Breakout (ORB) - popular intraday strategy used by day traders."""
    try:
        data = get_stock_data(symbol, period="1d", interval="5m")
        if data is None or len(data) < 6:
            return None
        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None
        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.005)
        # First 3 candles (15 minutes) define opening range
        or_high = float(data["High"].iloc[:3].max())
        or_low = float(data["Low"].iloc[:3].min())
        signal = None
        confidence = 0.7
        reason = ""
        if ltp > or_high:
            signal = "BUY"
            reason = f"ORB Breakout above ₹{or_high:.0f} (15-min opening range high)"
            confidence = 0.72
        elif ltp < or_low:
            signal = "SELL"
            reason = f"ORB Breakdown below ₹{or_low:.0f} (15-min opening range low)"
            confidence = 0.72
        else:
            return None
        or_range = or_high - or_low
        if signal == "BUY":
            stop_loss = round(or_low, 2)
            target = round(ltp + or_range * 2, 2)
        else:
            stop_loss = round(or_high, 2)
            target = round(ltp - or_range * 2, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0
        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "ORB_STRATEGY",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "EQUITY",
            "reason": reason,
        }
    except Exception as e:
        logger.error(f"ORB error for {symbol}: {e}")
        return None
from app.services.options_strategies import (
    analyze_long_call,
    analyze_bull_call_spread,
    analyze_long_call_butterfly,
    analyze_call_ratio_backspread,
    analyze_long_call_condor,
    analyze_long_put,
    analyze_bear_put_spread,
    analyze_long_put_butterfly,
    analyze_put_ratio_backspread,
    analyze_long_straddle,
    analyze_long_strangle,
)
from app.services.stock_options_strategies import (
    analyze_covered_call,
    analyze_protective_put,
    analyze_collar,
    analyze_synthetic_long,
    analyze_synthetic_short,
    analyze_stock_repair,
    analyze_delta_neutral_hedge,
)
from app.services.greeks_analyzer import (
    analyze_delta_directional,
    analyze_gamma_scalping,
    analyze_iv_crush_play,
    analyze_iv_expansion_play,
    analyze_oi_breakout,
    analyze_pcr_reversal,
    analyze_max_pain_magnet,
    analyze_gex_strategy,
)

STRATEGY_ANALYZERS = {
    # Equity strategies
    "MA_CROSSOVER": analyze_ma_crossover,
    "RSI_DIVERGENCE": analyze_rsi_divergence,
    "MACD_SIGNAL": analyze_macd_signal,
    "FIBONACCI_RETRACEMENT": analyze_fibonacci,
    "BOLLINGER_BREAKOUT": analyze_bollinger_breakout,
    "SUPERTREND": analyze_supertrend,
    "VWAP_STRATEGY": analyze_vwap,
    "ORDER_BLOCK": analyze_order_block,
    "SUPPLY_DEMAND": analyze_supply_demand,
    "EMA_RIBBON": analyze_ema_ribbon,
    "VOLUME_BREAKOUT": analyze_volume_breakout,
    "ICT_FVG": analyze_ict_fair_value_gap,
    "ORB_STRATEGY": analyze_opening_range_breakout,
    # Call-side options buying strategies
    "LONG_CALL": analyze_long_call,
    "BULL_CALL_SPREAD": analyze_bull_call_spread,
    "LONG_CALL_BUTTERFLY": analyze_long_call_butterfly,
    "CALL_RATIO_BACKSPREAD": analyze_call_ratio_backspread,
    "LONG_CALL_CONDOR": analyze_long_call_condor,
    # Put-side options buying strategies
    "LONG_PUT": analyze_long_put,
    "BEAR_PUT_SPREAD": analyze_bear_put_spread,
    "LONG_PUT_BUTTERFLY": analyze_long_put_butterfly,
    "PUT_RATIO_BACKSPREAD": analyze_put_ratio_backspread,
    # Volatility options strategies
    "LONG_STRADDLE": analyze_long_straddle,
    "LONG_STRANGLE": analyze_long_strangle,
    # Stock + options combined strategies
    "COVERED_CALL": analyze_covered_call,
    "PROTECTIVE_PUT": analyze_protective_put,
    "COLLAR": analyze_collar,
    "SYNTHETIC_LONG": analyze_synthetic_long,
    "SYNTHETIC_SHORT": analyze_synthetic_short,
    "STOCK_REPAIR": analyze_stock_repair,
    "DELTA_NEUTRAL_HEDGE": analyze_delta_neutral_hedge,
    # Greeks-based strategies
    "DELTA_DIRECTIONAL": analyze_delta_directional,
    "GAMMA_SCALPING": analyze_gamma_scalping,
    "IV_CRUSH_PLAY": analyze_iv_crush_play,
    "IV_EXPANSION_PLAY": analyze_iv_expansion_play,
    "OI_BREAKOUT": analyze_oi_breakout,
    "PCR_REVERSAL": analyze_pcr_reversal,
    "MAX_PAIN_MAGNET": analyze_max_pain_magnet,
    "GEX_STRATEGY": analyze_gex_strategy,
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
