"""
Stock and Stock Options Combined Strategies.

These strategies combine stock positions with options for enhanced returns,
hedging, or income generation. They analyze both equity technicals and
options chain data including Greeks.

Strategies:
- Covered Call: Own stock + sell OTM call (income generation)
- Protective Put / Married Put: Own stock + buy put (portfolio insurance)
- Collar: Own stock + buy OTM put + sell OTM call (hedged position)
- Synthetic Long Stock: Buy ATM call + sell ATM put (leveraged stock exposure)
- Synthetic Short Stock: Buy ATM put + sell ATM call (leveraged short)
- Covered Put (Short Stock + Sell Put): Income on short positions
- Stock Repair Strategy: Own losing stock + bull call spread (recovery)
- Dividend Capture with Options: Stock + options around ex-dividend
- Delta-Neutral Stock + Options: Stock position hedged with options

References:
- McMillan, L.G. "Options as a Strategic Investment"
- Fontanills, G.A. "The Options Course"
- Passarelli, D. "Trading Option Greeks"
"""

import numpy as np
from typing import Optional
from app.services.nse_data import (
    get_historical_data,
    get_stock_quote,
    get_option_chain,
)
from app.services.technical_analysis import calculate_indicators
from app.services.options_greeks import (
    calculate_all_greeks,
    calculate_delta,
    calculate_pcr,
    calculate_max_pain,
    analyze_oi_buildup,
    analyze_iv_skew,
)
import logging

logger = logging.getLogger(__name__)

DEFAULT_RISK_FREE_RATE = 0.065
DEFAULT_MONTHLY_EXPIRY_DAYS = 30


def _get_atm_strike(spot_price: float, option_chain: list[dict]) -> Optional[dict]:
    if not option_chain:
        return None
    return min(option_chain, key=lambda x: abs(x["strike_price"] - spot_price))


def _get_strike_by_offset(
    spot_price: float, option_chain: list[dict], offset_pct: float
) -> Optional[dict]:
    target_strike = spot_price * (1 + offset_pct)
    if not option_chain:
        return None
    return min(option_chain, key=lambda x: abs(x["strike_price"] - target_strike))


def _estimate_option_iv(entry: dict, option_type: str = "call") -> float:
    if option_type == "call":
        iv = entry.get("call_iv")
    else:
        iv = entry.get("put_iv")
    if iv and iv > 0:
        return iv / 100
    return 0.20


def _days_to_years(days: int) -> float:
    return days / 365.0


def analyze_covered_call(symbol: str) -> Optional[dict]:
    """
    Covered Call: Long stock + Sell OTM Call.

    Best when:
    - Mildly bullish or neutral on stock
    - Want to generate income from existing holdings
    - IV is relatively high (more premium collected)
    - Stock has limited upside in near term

    Max Profit: (Strike - Stock Price) + Premium received
    Max Loss: Stock price - Premium received (stock drops to zero)
    Breakeven: Stock purchase price - Premium received
    """
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 30:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None

        ltp = quote["ltp"]
        rsi = indicators.get("rsi", 50)
        atr = indicators.get("atr", ltp * 0.02)
        adx = indicators.get("adx", 20)
        ema_9 = indicators.get("ema_9", ltp)
        ema_21 = indicators.get("ema_21", ltp)

        score = 0
        reasons = []

        # Mildly bullish or neutral conditions
        if 40 < rsi < 65:
            score += 1
            reasons.append(f"RSI={rsi} neutral-bullish")
        if adx < 30:
            score += 1
            reasons.append(f"ADX={adx} moderate trend")
        if ema_9 >= ema_21 * 0.99:
            score += 1
            reasons.append("EMAs aligned or flat")
        if ltp > indicators.get("sma_50", 0):
            score += 1
            reasons.append("Above SMA 50 (healthy trend)")

        if score < 2:
            return None

        option_chain = get_option_chain(symbol)
        strategy_info = ""

        if option_chain:
            otm_call = _get_strike_by_offset(ltp, option_chain, 0.03)
            if otm_call:
                premium = otm_call["call_ltp"]
                strike = otm_call["strike_price"]
                max_profit = round((strike - ltp) + premium, 2)
                breakeven = round(ltp - premium, 2)
                yield_pct = round((premium / ltp) * 100, 2)
                annualized_yield = round(yield_pct * (365 / DEFAULT_MONTHLY_EXPIRY_DAYS), 2)

                iv = _estimate_option_iv(otm_call, "call")
                T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                greeks = calculate_all_greeks(
                    ltp, strike, T, DEFAULT_RISK_FREE_RATE, iv, "call"
                )

                strategy_info = (
                    f" | Sell {strike}CE @{premium}, "
                    f"Yield={yield_pct}% ({annualized_yield}% annualized), "
                    f"Max Profit={max_profit}, Breakeven={breakeven}, "
                    f"Short Delta={-greeks['delta']:.4f}, Theta Income={-greeks['theta']:.4f}/day"
                )

                # Higher IV = more premium = better for covered calls
                if iv > 0.25:
                    score += 1
                    reasons.append(f"IV={iv*100:.0f}% elevated (more premium)")

        confidence = min(0.5 + score * 0.08, 0.88)
        target = round(ltp + 2 * atr, 2)
        stop_loss = round(ltp - 2 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "COVERED_CALL",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Covered Call: {', '.join(reasons[:3])}{strategy_info}",
        }
    except Exception as e:
        logger.error(f"Covered Call error for {symbol}: {e}")
        return None


def analyze_protective_put(symbol: str) -> Optional[dict]:
    """
    Protective Put (Married Put): Long stock + Buy OTM Put.

    Best when:
    - Bullish long-term but worried about near-term downside
    - Want insurance on existing stock holdings
    - Before earnings or events that could cause sharp drops
    - Portfolio has concentrated stock positions

    Max Profit: Unlimited (stock rises)
    Max Loss: (Stock Price - Strike) + Premium paid
    Breakeven: Stock price + Premium paid
    """
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 30:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None

        ltp = quote["ltp"]
        rsi = indicators.get("rsi", 50)
        atr = indicators.get("atr", ltp * 0.02)
        ema_9 = indicators.get("ema_9", ltp)
        ema_21 = indicators.get("ema_21", ltp)

        score = 0
        reasons = []

        # Bullish but with risk concerns
        if ltp > indicators.get("sma_50", 0):
            score += 1
            reasons.append("Long-term bullish (above SMA 50)")
        if rsi > 60:
            score += 1
            reasons.append(f"RSI={rsi} elevated - protection warranted")
        if ema_9 > ema_21:
            score += 1
            reasons.append("Short-term uptrend intact")

        # Volatility increasing
        closes = data["Close"].values
        recent_vol = float(np.std(closes[-10:]) / np.mean(closes[-10:]) * 100)
        hist_vol = float(np.std(closes[-30:]) / np.mean(closes[-30:]) * 100)
        if recent_vol > hist_vol * 1.2:
            score += 1
            reasons.append(f"Volatility expanding ({recent_vol:.1f}% vs {hist_vol:.1f}%)")

        if score < 2:
            return None

        option_chain = get_option_chain(symbol)
        strategy_info = ""

        if option_chain:
            otm_put = _get_strike_by_offset(ltp, option_chain, -0.05)
            if otm_put:
                premium = otm_put["put_ltp"]
                strike = otm_put["strike_price"]
                max_loss = round((ltp - strike) + premium, 2)
                breakeven = round(ltp + premium, 2)
                cost_pct = round((premium / ltp) * 100, 2)

                strategy_info = (
                    f" | Buy {strike}PE @{premium} (cost={cost_pct}%), "
                    f"Floor at {strike}, Max Loss={max_loss}, "
                    f"Breakeven={breakeven}"
                )

                # Check OI for support levels
                oi_data = analyze_oi_buildup(option_chain, ltp)
                if oi_data.get("support_from_oi"):
                    reasons.append(f"Put OI support at {oi_data['support_from_oi']}")

        confidence = min(0.5 + score * 0.08, 0.85)
        target = round(ltp + 3 * atr, 2)
        stop_loss = round(ltp - 3 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "PROTECTIVE_PUT",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Protective Put: {', '.join(reasons[:3])}{strategy_info}",
        }
    except Exception as e:
        logger.error(f"Protective Put error for {symbol}: {e}")
        return None


def analyze_collar(symbol: str) -> Optional[dict]:
    """
    Collar: Long Stock + Buy OTM Put + Sell OTM Call.

    Best when:
    - Want to protect stock holdings at low/zero cost
    - Willing to cap upside for downside protection
    - Neutral to mildly bullish
    - Great for large concentrated positions

    Max Profit: Call strike - Stock price + Net premium
    Max Loss: Stock price - Put strike + Net premium
    Breakeven: Stock price + Net debit (or - net credit)
    """
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 30:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None

        ltp = quote["ltp"]
        rsi = indicators.get("rsi", 50)
        atr = indicators.get("atr", ltp * 0.02)
        adx = indicators.get("adx", 20)

        score = 0
        reasons = []

        if ltp > indicators.get("sma_50", 0):
            score += 1
            reasons.append("Above SMA 50 (worth protecting)")
        if 40 < rsi < 70:
            score += 1
            reasons.append(f"RSI={rsi}")
        if adx < 30:
            score += 1
            reasons.append(f"ADX={adx} moderate")

        if score < 2:
            return None

        option_chain = get_option_chain(symbol)
        collar_info = ""

        if option_chain:
            otm_call = _get_strike_by_offset(ltp, option_chain, 0.04)
            otm_put = _get_strike_by_offset(ltp, option_chain, -0.04)

            if otm_call and otm_put:
                call_premium = otm_call["call_ltp"]
                put_premium = otm_put["put_ltp"]
                net_cost = round(put_premium - call_premium, 2)
                max_profit = round(otm_call["strike_price"] - ltp - net_cost, 2)
                max_loss = round(ltp - otm_put["strike_price"] + net_cost, 2)

                collar_info = (
                    f" | Sell {otm_call['strike_price']}CE @{call_premium}, "
                    f"Buy {otm_put['strike_price']}PE @{put_premium}, "
                    f"Net {'Debit' if net_cost > 0 else 'Credit'}={abs(net_cost)}, "
                    f"Max Profit={max_profit}, Max Loss={max_loss}, "
                    f"Range: {otm_put['strike_price']}-{otm_call['strike_price']}"
                )

                if abs(net_cost) < ltp * 0.005:
                    score += 1
                    reasons.append("Near zero-cost collar")

        confidence = min(0.5 + score * 0.08, 0.85)
        target = round(ltp + 2 * atr, 2)
        stop_loss = round(ltp - 2 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "COLLAR",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Collar: {', '.join(reasons[:3])}{collar_info}",
        }
    except Exception as e:
        logger.error(f"Collar error for {symbol}: {e}")
        return None


def analyze_synthetic_long(symbol: str) -> Optional[dict]:
    """
    Synthetic Long Stock: Buy ATM Call + Sell ATM Put.

    Best when:
    - Strongly bullish with limited capital
    - Want stock-like exposure with less capital
    - Delta ~1.0 (mimics owning stock)
    - Lower margin requirement than buying stock outright

    Profit/Loss: Mirrors stock movement 1:1
    Breakeven: Strike price + Net debit
    """
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 30:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None

        ltp = quote["ltp"]
        rsi = indicators.get("rsi", 50)
        atr = indicators.get("atr", ltp * 0.02)
        ema_9 = indicators.get("ema_9", ltp)
        ema_21 = indicators.get("ema_21", ltp)
        supertrend_dir = indicators.get("supertrend_direction", "")

        bullish_score = 0
        reasons = []

        if ema_9 > ema_21:
            bullish_score += 1
            reasons.append("EMA bullish crossover")
        if rsi > 50 and rsi < 75:
            bullish_score += 1
            reasons.append(f"RSI={rsi} bullish")
        if supertrend_dir == "UP":
            bullish_score += 1
            reasons.append("Supertrend UP")
        if indicators.get("macd_histogram", 0) > 0:
            bullish_score += 1
            reasons.append("MACD positive")
        if ltp > indicators.get("sma_50", 0):
            bullish_score += 1
            reasons.append("Above SMA 50")

        if bullish_score < 3:
            return None

        option_chain = get_option_chain(symbol)
        synthetic_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            if atm:
                call_premium = atm["call_ltp"]
                put_premium = atm["put_ltp"]
                net_cost = round(call_premium - put_premium, 2)
                breakeven = round(atm["strike_price"] + net_cost, 2)

                iv = _estimate_option_iv(atm, "call")
                T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                call_greeks = calculate_all_greeks(
                    ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "call"
                )
                put_greeks = calculate_all_greeks(
                    ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "put"
                )
                net_delta = round(call_greeks["delta"] - put_greeks["delta"], 4)

                synthetic_info = (
                    f" | Buy {atm['strike_price']}CE @{call_premium}, "
                    f"Sell {atm['strike_price']}PE @{put_premium}, "
                    f"Net {'Debit' if net_cost > 0 else 'Credit'}={abs(net_cost)}, "
                    f"Breakeven={breakeven}, Net Delta={net_delta} (stock-like)"
                )

        confidence = min(0.5 + bullish_score * 0.07, 0.88)
        target = round(ltp + 3 * atr, 2)
        stop_loss = round(ltp - 2 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "SYNTHETIC_LONG",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Synthetic Long: {', '.join(reasons[:3])}{synthetic_info}",
        }
    except Exception as e:
        logger.error(f"Synthetic Long error for {symbol}: {e}")
        return None


def analyze_synthetic_short(symbol: str) -> Optional[dict]:
    """
    Synthetic Short Stock: Buy ATM Put + Sell ATM Call.

    Best when:
    - Strongly bearish
    - Want short-stock exposure without borrowing shares
    - Delta ~ -1.0 (mimics shorting stock)
    - Avoids short-selling restrictions

    Profit/Loss: Mirrors inverse stock movement 1:1
    Breakeven: Strike price - Net credit
    """
    try:
        data = get_historical_data(symbol, period="3mo", interval="1d")
        if data is None or len(data) < 30:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None

        ltp = quote["ltp"]
        rsi = indicators.get("rsi", 50)
        atr = indicators.get("atr", ltp * 0.02)
        ema_9 = indicators.get("ema_9", ltp)
        ema_21 = indicators.get("ema_21", ltp)
        supertrend_dir = indicators.get("supertrend_direction", "")

        bearish_score = 0
        reasons = []

        if ema_9 < ema_21:
            bearish_score += 1
            reasons.append("EMA bearish crossover")
        if rsi > 60:
            bearish_score += 1
            reasons.append(f"RSI={rsi} overbought, reversal expected")
        if supertrend_dir == "DOWN":
            bearish_score += 1
            reasons.append("Supertrend DOWN")
        if indicators.get("macd_histogram", 0) < 0:
            bearish_score += 1
            reasons.append("MACD negative")
        if ltp < indicators.get("sma_50", ltp):
            bearish_score += 1
            reasons.append("Below SMA 50")

        if bearish_score < 3:
            return None

        option_chain = get_option_chain(symbol)
        synthetic_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            if atm:
                call_premium = atm["call_ltp"]
                put_premium = atm["put_ltp"]
                net_cost = round(put_premium - call_premium, 2)
                breakeven = round(atm["strike_price"] - net_cost, 2) if net_cost > 0 else round(atm["strike_price"] + abs(net_cost), 2)

                synthetic_info = (
                    f" | Buy {atm['strike_price']}PE @{put_premium}, "
                    f"Sell {atm['strike_price']}CE @{call_premium}, "
                    f"Breakeven={breakeven}"
                )

        confidence = min(0.5 + bearish_score * 0.07, 0.88)
        target = round(ltp - 3 * atr, 2)
        stop_loss = round(ltp + 2 * atr, 2)
        risk = abs(stop_loss - ltp)
        reward = abs(ltp - target)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "SELL",
            "strategy": "SYNTHETIC_SHORT",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Synthetic Short: {', '.join(reasons[:3])}{synthetic_info}",
        }
    except Exception as e:
        logger.error(f"Synthetic Short error for {symbol}: {e}")
        return None


def analyze_stock_repair(symbol: str) -> Optional[dict]:
    """
    Stock Repair Strategy: For stocks that have fallen, use a bull call spread to recover.

    Own stock at loss + Buy 1 ATM Call + Sell 2 OTM Calls at original purchase price.

    Best when:
    - Stock has fallen 10-30% from recent highs
    - Moderately bullish on recovery
    - Want to reduce breakeven without adding more capital
    - Zero or low cost (call spread can be set up at zero cost)

    Doubles the recovery rate: stock needs to recover only half the loss.
    """
    try:
        data = get_historical_data(symbol, period="6mo", interval="1d")
        if data is None or len(data) < 50:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None

        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.02)

        # Check if stock has fallen significantly from highs
        high_3m = float(np.max(data["High"].values[-60:]))
        decline_pct = (high_3m - ltp) / high_3m * 100

        if decline_pct < 8 or decline_pct > 40:
            return None

        score = 0
        reasons = []

        reasons.append(f"Stock down {decline_pct:.1f}% from 3-month high ({high_3m:.0f})")

        # Check for recovery signs
        rsi = indicators.get("rsi", 50)
        if rsi < 45:
            score += 1
            reasons.append(f"RSI={rsi} oversold, recovery potential")
        if indicators.get("macd_histogram", 0) > 0:
            score += 1
            reasons.append("MACD turning positive")
        if indicators.get("supertrend_direction", "") == "UP":
            score += 1
            reasons.append("Supertrend turning bullish")

        # Volume pickup on recovery days
        volumes = data["Volume"].values
        closes = data["Close"].values
        if len(closes) > 5:
            recent_up_vol = np.mean([volumes[i] for i in range(-5, 0) if closes[i] > closes[i-1]] or [0])
            avg_vol = np.mean(volumes[-20:])
            if recent_up_vol > avg_vol * 1.2:
                score += 1
                reasons.append("Recovery volume increasing")

        if score < 1:
            return None

        option_chain = get_option_chain(symbol)
        repair_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            target_strike = _get_strike_by_offset(ltp, option_chain, decline_pct / 200)

            if atm and target_strike and atm["strike_price"] != target_strike["strike_price"]:
                buy_premium = atm["call_ltp"]
                sell_premium = target_strike["call_ltp"]
                net_cost = round(buy_premium - 2 * sell_premium, 2)
                new_breakeven = round(ltp + (high_3m - ltp) / 2, 2)

                repair_info = (
                    f" | Buy 1x{atm['strike_price']}CE @{buy_premium}, "
                    f"Sell 2x{target_strike['strike_price']}CE @{sell_premium}, "
                    f"Net {'Debit' if net_cost > 0 else 'Credit'}={abs(net_cost)}, "
                    f"New Breakeven ~{new_breakeven} (half the recovery needed)"
                )

        confidence = min(0.45 + score * 0.1, 0.80)
        target = round(ltp + (high_3m - ltp) * 0.5, 2)
        stop_loss = round(ltp - 2 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "STOCK_REPAIR",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Stock Repair: {', '.join(reasons[:3])}{repair_info}",
        }
    except Exception as e:
        logger.error(f"Stock Repair error for {symbol}: {e}")
        return None


def analyze_delta_neutral_hedge(symbol: str) -> Optional[dict]:
    """
    Delta-Neutral Stock Hedge: Long stock + buy puts to make delta neutral.

    Best when:
    - Want to hedge existing stock position
    - Expecting high volatility event
    - Want to profit from gamma (large moves) while being direction-neutral
    - Before earnings, budget, or major events

    Profits from: Large moves in either direction (gamma profit)
    Risk: Time decay (theta) eats into position
    """
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
        adx = indicators.get("adx", 20)
        bb_upper = indicators.get("bollinger_upper", ltp * 1.04)
        bb_lower = indicators.get("bollinger_lower", ltp * 0.96)

        score = 0
        reasons = []

        # Conditions for delta-neutral: expecting volatility
        bb_width = (bb_upper - bb_lower) / ltp * 100
        if bb_width < 6:
            score += 1
            reasons.append(f"Bollinger squeeze ({bb_width:.1f}%)")

        closes = data["Close"].values
        recent_vol = float(np.std(closes[-5:]) / np.mean(closes[-5:]) * 100)
        hist_vol = float(np.std(closes[-30:]) / np.mean(closes[-30:]) * 100)
        if recent_vol < hist_vol * 0.6:
            score += 1
            reasons.append(f"Volatility compressed (recent={recent_vol:.1f}% vs hist={hist_vol:.1f}%)")

        if adx < 20:
            score += 1
            reasons.append(f"ADX={adx} low - breakout setup")

        if score < 2:
            return None

        option_chain = get_option_chain(symbol)
        hedge_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            if atm:
                iv = _estimate_option_iv(atm, "put")
                T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                put_greeks = calculate_all_greeks(
                    ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "put"
                )

                put_delta = abs(put_greeks["delta"])
                # Hedge ratio: number of puts to buy per 100 shares
                hedge_ratio = round(1 / put_delta, 0) if put_delta > 0 else 2
                total_gamma = round(put_greeks["gamma"] * hedge_ratio, 6)

                hedge_info = (
                    f" | Buy {int(hedge_ratio)}x {atm['strike_price']}PE @{atm['put_ltp']} "
                    f"per 100 shares, Delta-neutral, "
                    f"Gamma={total_gamma} (profits from big moves), "
                    f"Theta={put_greeks['theta'] * hedge_ratio:.4f}/day (cost of hedge)"
                )

        confidence = min(0.45 + score * 0.1, 0.80)
        target = round(ltp + 3 * atr, 2)
        stop_loss = round(ltp - 3 * atr, 2)

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "DELTA_NEUTRAL_HEDGE",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": 2.0,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Delta-Neutral Hedge: {', '.join(reasons[:3])}{hedge_info}",
        }
    except Exception as e:
        logger.error(f"Delta Neutral error for {symbol}: {e}")
        return None
