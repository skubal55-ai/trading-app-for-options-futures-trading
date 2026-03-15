import pandas as pd
import numpy as np
import ta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def calculate_indicators(data: pd.DataFrame) -> dict:
    if data is None or data.empty or len(data) < 5:
        return {}

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    volume = data["Volume"]

    indicators = {}

    try:
        if len(close) >= 20:
            indicators["sma_20"] = round(float(ta.trend.sma_indicator(close, window=20).iloc[-1]), 2)
        if len(close) >= 50:
            indicators["sma_50"] = round(float(ta.trend.sma_indicator(close, window=50).iloc[-1]), 2)
        if len(close) >= 200:
            indicators["sma_200"] = round(float(ta.trend.sma_indicator(close, window=200).iloc[-1]), 2)

        if len(close) >= 9:
            indicators["ema_9"] = round(float(ta.trend.ema_indicator(close, window=9).iloc[-1]), 2)
        if len(close) >= 21:
            indicators["ema_21"] = round(float(ta.trend.ema_indicator(close, window=21).iloc[-1]), 2)

        if len(close) >= 14:
            indicators["rsi"] = round(float(ta.momentum.rsi(close, window=14).iloc[-1]), 2)

        if len(close) >= 26:
            macd_obj = ta.trend.MACD(close)
            indicators["macd"] = round(float(macd_obj.macd().iloc[-1]), 2)
            indicators["macd_signal"] = round(float(macd_obj.macd_signal().iloc[-1]), 2)
            indicators["macd_histogram"] = round(float(macd_obj.macd_diff().iloc[-1]), 2)

        if len(close) >= 20:
            bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
            indicators["bollinger_upper"] = round(float(bb.bollinger_hband().iloc[-1]), 2)
            indicators["bollinger_middle"] = round(float(bb.bollinger_mavg().iloc[-1]), 2)
            indicators["bollinger_lower"] = round(float(bb.bollinger_lband().iloc[-1]), 2)

        if len(close) >= 14:
            indicators["atr"] = round(float(ta.volatility.average_true_range(high, low, close, window=14).iloc[-1]), 2)

        if len(close) >= 14:
            indicators["adx"] = round(float(ta.trend.adx(high, low, close, window=14).iloc[-1]), 2)

        indicators.update(_calculate_supertrend(data))

        if len(data) >= 14:
            stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
            indicators["stochastic_k"] = round(float(stoch.stoch().iloc[-1]), 2)
            indicators["stochastic_d"] = round(float(stoch.stoch_signal().iloc[-1]), 2)

        if len(data) >= 1:
            typical_price = (high + low + close) / 3
            cumulative_tp_vol = (typical_price * volume).cumsum()
            cumulative_vol = volume.cumsum()
            vwap = cumulative_tp_vol / cumulative_vol
            indicators["vwap"] = round(float(vwap.iloc[-1]), 2)

    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")

    return indicators


def _calculate_supertrend(data: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> dict:
    try:
        close = data["Close"]
        high = data["High"]
        low = data["Low"]

        if len(data) < period:
            return {}

        atr = ta.volatility.average_true_range(high, low, close, window=period)

        hl2 = (high + low) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        supertrend = pd.Series(index=data.index, dtype=float)
        direction = pd.Series(index=data.index, dtype=float)

        supertrend.iloc[0] = upper_band.iloc[0]
        direction.iloc[0] = -1

        for i in range(1, len(data)):
            if close.iloc[i] > upper_band.iloc[i - 1]:
                direction.iloc[i] = 1
            elif close.iloc[i] < lower_band.iloc[i - 1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i - 1]

            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                supertrend.iloc[i] = upper_band.iloc[i]

        return {
            "supertrend": round(float(supertrend.iloc[-1]), 2),
            "supertrend_direction": "UP" if direction.iloc[-1] == 1 else "DOWN",
        }
    except Exception as e:
        logger.error(f"Error calculating supertrend: {e}")
        return {}


def calculate_fibonacci_levels(data: pd.DataFrame) -> dict:
    if data is None or data.empty:
        return {}

    try:
        high = float(data["High"].max())
        low = float(data["Low"].min())
        diff = high - low

        current_close = float(data["Close"].iloc[-1])
        trend = "UP" if current_close > (high + low) / 2 else "DOWN"

        if trend == "UP":
            levels = {
                "trend": "UP",
                "level_0": round(low, 2),
                "level_236": round(low + 0.236 * diff, 2),
                "level_382": round(low + 0.382 * diff, 2),
                "level_500": round(low + 0.5 * diff, 2),
                "level_618": round(low + 0.618 * diff, 2),
                "level_786": round(low + 0.786 * diff, 2),
                "level_1": round(high, 2),
            }
        else:
            levels = {
                "trend": "DOWN",
                "level_0": round(high, 2),
                "level_236": round(high - 0.236 * diff, 2),
                "level_382": round(high - 0.382 * diff, 2),
                "level_500": round(high - 0.5 * diff, 2),
                "level_618": round(high - 0.618 * diff, 2),
                "level_786": round(high - 0.786 * diff, 2),
                "level_1": round(low, 2),
            }

        return levels
    except Exception as e:
        logger.error(f"Error calculating fibonacci: {e}")
        return {}


def calculate_pivot_points(data: pd.DataFrame) -> dict:
    if data is None or data.empty:
        return {}

    try:
        last = data.iloc[-1]
        high = float(last["High"])
        low = float(last["Low"])
        close = float(last["Close"])

        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        s1 = 2 * pivot - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2 * (pivot - low)
        s3 = low - 2 * (high - pivot)

        return {
            "pivot": round(pivot, 2),
            "r1": round(r1, 2),
            "r2": round(r2, 2),
            "r3": round(r3, 2),
            "s1": round(s1, 2),
            "s2": round(s2, 2),
            "s3": round(s3, 2),
        }
    except Exception as e:
        logger.error(f"Error calculating pivot points: {e}")
        return {}
