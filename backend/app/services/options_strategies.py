"""
Options Buying Strategies - Call Side and Put Side.

Implements advanced options trading strategies that analyze underlying price action,
technical indicators, options chain data, and Greeks to generate actionable signals.

Call-Side Strategies:
- Long Call (directional bullish)
- Bull Call Spread (limited risk bullish)
- Long Call Butterfly (range-bound, low cost)
- Call Ratio Backspread (unlimited upside, limited downside)
- Long Call Condor (range-bound with wider profit zone)
- Synthetic Long Call via Bull Call Ladder

Put-Side Strategies:
- Long Put (directional bearish)
- Bear Put Spread (limited risk bearish)
- Long Put Butterfly (range-bound, low cost)
- Put Ratio Backspread (unlimited downside profit, limited upside risk)
- Long Put Condor (range-bound with wider profit zone)
- Protective/Married Put (portfolio insurance)

References:
- McMillan, L.G. "Options as a Strategic Investment"
- Natenberg, S. "Option Volatility and Pricing"
- Cohen, G. "The Bible of Options Strategies"
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
    calculate_gamma,
    calculate_pcr,
    calculate_max_pain,
    analyze_oi_buildup,
    analyze_iv_skew,
    estimate_iv,
    calculate_iv_rank,
    calculate_moneyness,
)
import logging

logger = logging.getLogger(__name__)

# Default risk-free rate for Indian markets (RBI repo rate approx)
DEFAULT_RISK_FREE_RATE = 0.065
# Default time to expiry for nearest weekly (in years)
DEFAULT_WEEKLY_EXPIRY_DAYS = 7
DEFAULT_MONTHLY_EXPIRY_DAYS = 30


def _get_atm_strike(spot_price: float, option_chain: list[dict]) -> Optional[dict]:
    """Find the ATM strike from option chain."""
    if not option_chain:
        return None
    return min(option_chain, key=lambda x: abs(x["strike_price"] - spot_price))


def _get_strike_by_offset(
    spot_price: float, option_chain: list[dict], offset_pct: float
) -> Optional[dict]:
    """Find a strike at a given % offset from spot."""
    target_strike = spot_price * (1 + offset_pct)
    if not option_chain:
        return None
    return min(option_chain, key=lambda x: abs(x["strike_price"] - target_strike))


def _estimate_option_iv(entry: dict, option_type: str = "call") -> float:
    """Get IV from option chain entry, with fallback."""
    if option_type == "call":
        iv = entry.get("call_iv")
    else:
        iv = entry.get("put_iv")
    if iv and iv > 0:
        return iv / 100  # Convert from percentage
    return 0.20  # Default 20% IV


def _days_to_years(days: int) -> float:
    return days / 365.0


# =============================================================================
# CALL-SIDE OPTIONS BUYING STRATEGIES
# =============================================================================


def analyze_long_call(symbol: str) -> Optional[dict]:
    """
    Long Call Strategy: Buy a call option for directional bullish bet.

    Best when:
    - Strong bullish signal from technicals
    - IV is relatively low (IV Rank < 30) - options are cheap
    - Delta > 0.5 (ATM or slightly ITM for higher probability)
    - Positive gamma allows acceleration of profits

    Risk: Limited to premium paid
    Reward: Unlimited upside
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
        macd_hist = indicators.get("macd_histogram", 0)
        ema_9 = indicators.get("ema_9", ltp)
        ema_21 = indicators.get("ema_21", ltp)
        atr = indicators.get("atr", ltp * 0.02)
        supertrend_dir = indicators.get("supertrend_direction", "")

        # Bullish conditions check
        bullish_score = 0
        reasons = []

        if rsi < 60 and rsi > 30:
            bullish_score += 1
            reasons.append(f"RSI at {rsi} - room to run")
        if macd_hist > 0:
            bullish_score += 1
            reasons.append("MACD histogram positive")
        if ema_9 > ema_21:
            bullish_score += 1
            reasons.append("EMA 9 above EMA 21 (bullish trend)")
        if ltp > ema_21:
            bullish_score += 1
            reasons.append("Price above EMA 21")
        if supertrend_dir == "UP":
            bullish_score += 1
            reasons.append("Supertrend bullish")

        if bullish_score < 3:
            return None

        # Get option chain for Greeks analysis
        option_chain = get_option_chain(symbol)
        chain_analysis = ""
        greeks_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            if atm:
                iv = _estimate_option_iv(atm, "call")
                T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                greeks = calculate_all_greeks(
                    ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "call"
                )
                delta = greeks["delta"]
                gamma = greeks["gamma"]
                theta = greeks["theta"]
                vega = greeks["vega"]

                greeks_info = (
                    f" | Greeks: Delta={delta}, Gamma={gamma}, "
                    f"Theta={theta}/day, Vega={vega}"
                )

                # PCR analysis
                pcr = calculate_pcr(option_chain)
                if pcr["pcr_oi"] > 1.0:
                    bullish_score += 1
                    reasons.append(f"PCR={pcr['pcr_oi']} (put heavy = bullish)")

                # Max Pain
                max_pain = calculate_max_pain(option_chain)
                if max_pain > ltp:
                    reasons.append(f"Max Pain at {max_pain} (above spot, bullish pull)")

                chain_analysis = f" | ATM Strike: {atm['strike_price']}, Premium: {atm['call_ltp']}"

        confidence = min(0.5 + bullish_score * 0.07, 0.92)

        target = round(ltp + 3 * atr, 2)
        stop_loss = round(ltp - 1.5 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "LONG_CALL",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Long Call: {', '.join(reasons[:3])}{chain_analysis}{greeks_info}",
        }
    except Exception as e:
        logger.error(f"Long Call error for {symbol}: {e}")
        return None


def analyze_bull_call_spread(symbol: str) -> Optional[dict]:
    """
    Bull Call Spread: Buy ATM call + Sell OTM call.

    Best when:
    - Moderately bullish outlook
    - IV is moderate to high (selling the OTM call offsets cost)
    - Want defined risk and lower capital outlay than naked call
    - Target price is near the short call strike

    Max Profit: Difference between strikes minus net debit
    Max Loss: Net debit paid
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
        adx = indicators.get("adx", 20)

        # Moderate bullish conditions
        bullish_score = 0
        reasons = []

        if ema_9 > ema_21:
            bullish_score += 1
            reasons.append("Short-term trend bullish")
        if 40 < rsi < 65:
            bullish_score += 1
            reasons.append(f"RSI={rsi} moderate bullish zone")
        if adx > 20:
            bullish_score += 1
            reasons.append(f"ADX={adx} trending")
        if indicators.get("macd_histogram", 0) > 0:
            bullish_score += 1
            reasons.append("MACD momentum positive")

        if bullish_score < 2:
            return None

        option_chain = get_option_chain(symbol)
        spread_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            otm_call = _get_strike_by_offset(ltp, option_chain, 0.03)

            if atm and otm_call and atm["strike_price"] != otm_call["strike_price"]:
                buy_premium = atm["call_ltp"]
                sell_premium = otm_call["call_ltp"]
                net_debit = round(buy_premium - sell_premium, 2)
                max_profit = round(
                    otm_call["strike_price"] - atm["strike_price"] - net_debit, 2
                )
                breakeven = round(atm["strike_price"] + net_debit, 2)

                iv = _estimate_option_iv(atm, "call")
                T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                buy_greeks = calculate_all_greeks(
                    ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "call"
                )
                sell_greeks = calculate_all_greeks(
                    ltp, otm_call["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "call"
                )
                net_delta = round(buy_greeks["delta"] - sell_greeks["delta"], 4)
                net_theta = round(buy_greeks["theta"] - sell_greeks["theta"], 4)

                spread_info = (
                    f" | Buy {atm['strike_price']}CE @{buy_premium}, "
                    f"Sell {otm_call['strike_price']}CE @{sell_premium}, "
                    f"Net Debit={net_debit}, Max Profit={max_profit}, "
                    f"Breakeven={breakeven}, Net Delta={net_delta}, Net Theta={net_theta}"
                )

                # OI analysis for resistance
                oi_analysis = analyze_oi_buildup(option_chain, ltp)
                if oi_analysis.get("resistance_from_oi"):
                    reasons.append(
                        f"OI resistance at {oi_analysis['resistance_from_oi']}"
                    )

        confidence = min(0.5 + bullish_score * 0.08, 0.88)
        target = round(ltp + 2.5 * atr, 2)
        stop_loss = round(ltp - 1.5 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "BULL_CALL_SPREAD",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Bull Call Spread: {', '.join(reasons[:3])}{spread_info}",
        }
    except Exception as e:
        logger.error(f"Bull Call Spread error for {symbol}: {e}")
        return None


def analyze_long_call_butterfly(symbol: str) -> Optional[dict]:
    """
    Long Call Butterfly: Buy 1 ITM call + Sell 2 ATM calls + Buy 1 OTM call.

    Best when:
    - Expecting price to stay near ATM at expiry (range-bound)
    - Low IV environment (cheap to set up)
    - Low cost strategy with defined risk
    - ADX < 20 (non-trending market)

    Max Profit: Difference between lower strike and middle strike minus net debit
    Max Loss: Net debit paid
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
        adx = indicators.get("adx", 25)
        atr = indicators.get("atr", ltp * 0.02)
        bb_upper = indicators.get("bollinger_upper", ltp * 1.04)
        bb_lower = indicators.get("bollinger_lower", ltp * 0.96)
        rsi = indicators.get("rsi", 50)

        # Range-bound conditions
        range_score = 0
        reasons = []

        if adx < 25:
            range_score += 1
            reasons.append(f"ADX={adx} non-trending")
        if 40 < rsi < 60:
            range_score += 1
            reasons.append(f"RSI={rsi} neutral zone")

        bb_width = (bb_upper - bb_lower) / ltp * 100
        if bb_width < 8:
            range_score += 1
            reasons.append(f"Bollinger width={bb_width:.1f}% narrow")

        if range_score < 2:
            return None

        option_chain = get_option_chain(symbol)
        butterfly_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            itm = _get_strike_by_offset(ltp, option_chain, -0.03)
            otm = _get_strike_by_offset(ltp, option_chain, 0.03)

            if atm and itm and otm:
                buy_itm = itm["call_ltp"]
                sell_atm = atm["call_ltp"]
                buy_otm = otm["call_ltp"]
                net_debit = round(buy_itm - 2 * sell_atm + buy_otm, 2)

                butterfly_info = (
                    f" | Buy {itm['strike_price']}CE @{buy_itm}, "
                    f"Sell 2x{atm['strike_price']}CE @{sell_atm}, "
                    f"Buy {otm['strike_price']}CE @{buy_otm}, "
                    f"Net Debit={net_debit}"
                )

                # IV skew analysis
                iv_skew = analyze_iv_skew(option_chain, ltp)
                if iv_skew.get("skew_type") == "FLAT":
                    range_score += 1
                    reasons.append("Flat IV skew supports range-bound view")

        confidence = min(0.45 + range_score * 0.1, 0.82)
        target = ltp  # butterfly profits when price stays near ATM
        stop_loss = round(ltp - 2 * atr, 2)

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "LONG_CALL_BUTTERFLY",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": 3.0,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Long Call Butterfly: {', '.join(reasons[:3])}{butterfly_info}",
        }
    except Exception as e:
        logger.error(f"Call Butterfly error for {symbol}: {e}")
        return None


def analyze_call_ratio_backspread(symbol: str) -> Optional[dict]:
    """
    Call Ratio Backspread: Sell 1 ITM/ATM call + Buy 2 OTM calls.

    Best when:
    - Strongly bullish with expectation of large move
    - IV is expected to increase (long vega position)
    - Before events (earnings, budget, etc.)
    - Want unlimited upside with limited/no downside risk

    Max Loss: Limited (at the long strike at expiry)
    Max Profit: Unlimited on upside
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
        macd_hist = indicators.get("macd_histogram", 0)
        supertrend_dir = indicators.get("supertrend_direction", "")

        # Strong bullish with breakout potential
        bullish_score = 0
        reasons = []

        if rsi > 50 and rsi < 75:
            bullish_score += 1
            reasons.append(f"RSI={rsi} bullish momentum")
        if adx > 25:
            bullish_score += 1
            reasons.append(f"ADX={adx} strong trend")
        if macd_hist > 0:
            bullish_score += 1
            reasons.append("MACD positive momentum")
        if supertrend_dir == "UP":
            bullish_score += 1
            reasons.append("Supertrend bullish")

        # Check for breakout potential (price near resistance)
        closes = data["Close"].values
        high_20 = float(np.max(data["High"].values[-20:]))
        if ltp >= high_20 * 0.97:
            bullish_score += 1
            reasons.append(f"Near 20-day high ({high_20:.0f}), breakout potential")

        if bullish_score < 3:
            return None

        option_chain = get_option_chain(symbol)
        spread_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            otm = _get_strike_by_offset(ltp, option_chain, 0.04)

            if atm and otm and atm["strike_price"] != otm["strike_price"]:
                sell_premium = atm["call_ltp"]
                buy_premium = otm["call_ltp"]
                net_cost = round(2 * buy_premium - sell_premium, 2)

                iv = _estimate_option_iv(atm, "call")
                T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                net_vega = round(
                    2 * calculate_all_greeks(ltp, otm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "call")["vega"]
                    - calculate_all_greeks(ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "call")["vega"],
                    4
                )

                spread_info = (
                    f" | Sell 1x{atm['strike_price']}CE @{sell_premium}, "
                    f"Buy 2x{otm['strike_price']}CE @{buy_premium}, "
                    f"Net={'Debit' if net_cost > 0 else 'Credit'} {abs(net_cost)}, "
                    f"Net Vega={net_vega} (benefits from IV rise)"
                )

        confidence = min(0.5 + bullish_score * 0.07, 0.88)
        target = round(ltp + 4 * atr, 2)
        stop_loss = round(ltp - 1.5 * atr, 2)
        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "CALL_RATIO_BACKSPREAD",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Call Ratio Backspread: {', '.join(reasons[:3])}{spread_info}",
        }
    except Exception as e:
        logger.error(f"Call Ratio Backspread error for {symbol}: {e}")
        return None


def analyze_long_call_condor(symbol: str) -> Optional[dict]:
    """
    Long Call Condor: Buy 1 deep ITM + Sell 1 ITM + Sell 1 OTM + Buy 1 deep OTM call.

    Best when:
    - Expecting price to stay within a wider range than butterfly
    - Low IV environment
    - Non-trending market
    - Want defined risk with wider profit zone

    Max Profit: Difference between 1st and 2nd strikes minus net debit
    Max Loss: Net debit paid
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
        adx = indicators.get("adx", 25)
        rsi = indicators.get("rsi", 50)
        atr = indicators.get("atr", ltp * 0.02)
        bb_upper = indicators.get("bollinger_upper", ltp * 1.04)
        bb_lower = indicators.get("bollinger_lower", ltp * 0.96)

        range_score = 0
        reasons = []

        if adx < 22:
            range_score += 1
            reasons.append(f"ADX={adx} weak trend")
        if 35 < rsi < 65:
            range_score += 1
            reasons.append(f"RSI={rsi} neutral")

        bb_width = (bb_upper - bb_lower) / ltp * 100
        if bb_width < 10:
            range_score += 1
            reasons.append(f"Bollinger width={bb_width:.1f}%")

        # Price near middle of recent range
        high_20 = float(np.max(data["High"].values[-20:]))
        low_20 = float(np.min(data["Low"].values[-20:]))
        mid = (high_20 + low_20) / 2
        if abs(ltp - mid) / ltp < 0.03:
            range_score += 1
            reasons.append("Price near mid-range")

        if range_score < 2:
            return None

        option_chain = get_option_chain(symbol)
        condor_info = ""

        if option_chain:
            s1 = _get_strike_by_offset(ltp, option_chain, -0.05)
            s2 = _get_strike_by_offset(ltp, option_chain, -0.02)
            s3 = _get_strike_by_offset(ltp, option_chain, 0.02)
            s4 = _get_strike_by_offset(ltp, option_chain, 0.05)

            if s1 and s2 and s3 and s4:
                condor_info = (
                    f" | Buy {s1['strike_price']}CE, Sell {s2['strike_price']}CE, "
                    f"Sell {s3['strike_price']}CE, Buy {s4['strike_price']}CE"
                )

        confidence = min(0.45 + range_score * 0.09, 0.80)
        target = ltp
        stop_loss = round(ltp - 2 * atr, 2)

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "LONG_CALL_CONDOR",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": 2.5,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Long Call Condor: {', '.join(reasons[:3])}{condor_info}",
        }
    except Exception as e:
        logger.error(f"Call Condor error for {symbol}: {e}")
        return None


# =============================================================================
# PUT-SIDE OPTIONS BUYING STRATEGIES
# =============================================================================


def analyze_long_put(symbol: str) -> Optional[dict]:
    """
    Long Put Strategy: Buy a put option for directional bearish bet.

    Best when:
    - Strong bearish signal from technicals
    - IV is relatively low (cheap puts)
    - Delta close to -0.5 (ATM)
    - Breakdown below key support levels

    Risk: Limited to premium paid
    Reward: Substantial (price can fall to zero)
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
        macd_hist = indicators.get("macd_histogram", 0)
        ema_9 = indicators.get("ema_9", ltp)
        ema_21 = indicators.get("ema_21", ltp)
        atr = indicators.get("atr", ltp * 0.02)
        supertrend_dir = indicators.get("supertrend_direction", "")

        bearish_score = 0
        reasons = []

        if rsi > 40 and rsi < 70:
            bearish_score += 1
            reasons.append(f"RSI at {rsi}")
        if rsi > 65:
            bearish_score += 1
            reasons.append(f"RSI overbought at {rsi} - reversal likely")
        if macd_hist < 0:
            bearish_score += 1
            reasons.append("MACD histogram negative")
        if ema_9 < ema_21:
            bearish_score += 1
            reasons.append("EMA 9 below EMA 21 (bearish)")
        if ltp < ema_21:
            bearish_score += 1
            reasons.append("Price below EMA 21")
        if supertrend_dir == "DOWN":
            bearish_score += 1
            reasons.append("Supertrend bearish")

        if bearish_score < 3:
            return None

        option_chain = get_option_chain(symbol)
        chain_analysis = ""
        greeks_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            if atm:
                iv = _estimate_option_iv(atm, "put")
                T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                greeks = calculate_all_greeks(
                    ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "put"
                )
                greeks_info = (
                    f" | Greeks: Delta={greeks['delta']}, Gamma={greeks['gamma']}, "
                    f"Theta={greeks['theta']}/day"
                )
                chain_analysis = (
                    f" | ATM Strike: {atm['strike_price']}, Put Premium: {atm['put_ltp']}"
                )

                pcr = calculate_pcr(option_chain)
                if pcr["pcr_oi"] < 0.7:
                    bearish_score += 1
                    reasons.append(f"PCR={pcr['pcr_oi']} (call heavy = contrarian bearish)")

        confidence = min(0.5 + bearish_score * 0.07, 0.92)
        target = round(ltp - 3 * atr, 2)
        stop_loss = round(ltp + 1.5 * atr, 2)
        risk = abs(stop_loss - ltp)
        reward = abs(ltp - target)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "SELL",
            "strategy": "LONG_PUT",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Long Put: {', '.join(reasons[:3])}{chain_analysis}{greeks_info}",
        }
    except Exception as e:
        logger.error(f"Long Put error for {symbol}: {e}")
        return None


def analyze_bear_put_spread(symbol: str) -> Optional[dict]:
    """
    Bear Put Spread: Buy ATM put + Sell OTM put.

    Best when:
    - Moderately bearish outlook
    - IV is moderate to high (selling OTM put offsets cost)
    - Want defined risk and lower cost than naked put
    - Expected move is limited (not a crash)

    Max Profit: Difference between strikes minus net debit
    Max Loss: Net debit paid
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
        adx = indicators.get("adx", 20)

        bearish_score = 0
        reasons = []

        if ema_9 < ema_21:
            bearish_score += 1
            reasons.append("Short-term trend bearish")
        if 35 < rsi < 60:
            bearish_score += 1
            reasons.append(f"RSI={rsi} moderate bearish")
        if adx > 20:
            bearish_score += 1
            reasons.append(f"ADX={adx} trending")
        if indicators.get("macd_histogram", 0) < 0:
            bearish_score += 1
            reasons.append("MACD negative momentum")

        if bearish_score < 2:
            return None

        option_chain = get_option_chain(symbol)
        spread_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            otm_put = _get_strike_by_offset(ltp, option_chain, -0.03)

            if atm and otm_put and atm["strike_price"] != otm_put["strike_price"]:
                buy_premium = atm["put_ltp"]
                sell_premium = otm_put["put_ltp"]
                net_debit = round(buy_premium - sell_premium, 2)
                max_profit = round(
                    atm["strike_price"] - otm_put["strike_price"] - net_debit, 2
                )
                breakeven = round(atm["strike_price"] - net_debit, 2)

                iv = _estimate_option_iv(atm, "put")
                T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                buy_greeks = calculate_all_greeks(
                    ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "put"
                )
                sell_greeks = calculate_all_greeks(
                    ltp, otm_put["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "put"
                )
                net_delta = round(buy_greeks["delta"] - sell_greeks["delta"], 4)

                spread_info = (
                    f" | Buy {atm['strike_price']}PE @{buy_premium}, "
                    f"Sell {otm_put['strike_price']}PE @{sell_premium}, "
                    f"Net Debit={net_debit}, Max Profit={max_profit}, "
                    f"Breakeven={breakeven}, Net Delta={net_delta}"
                )

        confidence = min(0.5 + bearish_score * 0.08, 0.88)
        target = round(ltp - 2.5 * atr, 2)
        stop_loss = round(ltp + 1.5 * atr, 2)
        risk = abs(stop_loss - ltp)
        reward = abs(ltp - target)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "SELL",
            "strategy": "BEAR_PUT_SPREAD",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Bear Put Spread: {', '.join(reasons[:3])}{spread_info}",
        }
    except Exception as e:
        logger.error(f"Bear Put Spread error for {symbol}: {e}")
        return None


def analyze_long_put_butterfly(symbol: str) -> Optional[dict]:
    """
    Long Put Butterfly: Buy 1 ITM put + Sell 2 ATM puts + Buy 1 OTM put.

    Best when:
    - Range-bound market with bearish tilt
    - Low IV environment
    - Expecting price to settle near the middle strike at expiry
    - Low cost entry

    Max Profit: Difference between upper strike and middle strike minus net debit
    Max Loss: Net debit paid
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
        adx = indicators.get("adx", 25)
        rsi = indicators.get("rsi", 50)
        atr = indicators.get("atr", ltp * 0.02)

        range_score = 0
        reasons = []

        if adx < 25:
            range_score += 1
            reasons.append(f"ADX={adx} non-trending")
        if 35 < rsi < 55:
            range_score += 1
            reasons.append(f"RSI={rsi} neutral-bearish")

        ema_9 = indicators.get("ema_9", ltp)
        ema_21 = indicators.get("ema_21", ltp)
        if ema_9 < ema_21:
            range_score += 1
            reasons.append("Mild bearish bias (EMA 9 < 21)")

        if range_score < 2:
            return None

        option_chain = get_option_chain(symbol)
        butterfly_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            itm_put = _get_strike_by_offset(ltp, option_chain, 0.03)
            otm_put = _get_strike_by_offset(ltp, option_chain, -0.03)

            if atm and itm_put and otm_put:
                butterfly_info = (
                    f" | Buy {itm_put['strike_price']}PE, "
                    f"Sell 2x{atm['strike_price']}PE, "
                    f"Buy {otm_put['strike_price']}PE"
                )

        confidence = min(0.45 + range_score * 0.1, 0.80)
        target = ltp
        stop_loss = round(ltp + 2 * atr, 2)

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "LONG_PUT_BUTTERFLY",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": 3.0,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Long Put Butterfly: {', '.join(reasons[:3])}{butterfly_info}",
        }
    except Exception as e:
        logger.error(f"Put Butterfly error for {symbol}: {e}")
        return None


def analyze_put_ratio_backspread(symbol: str) -> Optional[dict]:
    """
    Put Ratio Backspread: Sell 1 ATM put + Buy 2 OTM puts.

    Best when:
    - Strongly bearish with expectation of large downward move
    - IV expected to increase (crash protection)
    - Want unlimited downside profit with limited upside risk
    - Great for black swan protection

    Max Loss: Limited (between the two strikes)
    Max Profit: Substantial (as price falls, profit from 2 long puts overwhelms)
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
        supertrend_dir = indicators.get("supertrend_direction", "")

        bearish_score = 0
        reasons = []

        if rsi > 55:
            bearish_score += 1
            reasons.append(f"RSI={rsi} potential reversal zone")
        if rsi > 70:
            bearish_score += 1
            reasons.append(f"RSI overbought at {rsi}")
        if indicators.get("macd_histogram", 0) < 0:
            bearish_score += 1
            reasons.append("MACD bearish")
        if supertrend_dir == "DOWN":
            bearish_score += 1
            reasons.append("Supertrend bearish")

        # Near support breakdown
        low_20 = float(np.min(data["Low"].values[-20:]))
        if ltp <= low_20 * 1.03:
            bearish_score += 1
            reasons.append(f"Near 20-day low ({low_20:.0f}), breakdown potential")

        if bearish_score < 3:
            return None

        option_chain = get_option_chain(symbol)
        spread_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            otm_put = _get_strike_by_offset(ltp, option_chain, -0.04)

            if atm and otm_put and atm["strike_price"] != otm_put["strike_price"]:
                sell_premium = atm["put_ltp"]
                buy_premium = otm_put["put_ltp"]
                net_cost = round(2 * buy_premium - sell_premium, 2)

                spread_info = (
                    f" | Sell 1x{atm['strike_price']}PE @{sell_premium}, "
                    f"Buy 2x{otm_put['strike_price']}PE @{buy_premium}, "
                    f"Net={'Debit' if net_cost > 0 else 'Credit'} {abs(net_cost)}"
                )

        confidence = min(0.5 + bearish_score * 0.07, 0.88)
        target = round(ltp - 4 * atr, 2)
        stop_loss = round(ltp + 1.5 * atr, 2)
        risk = abs(stop_loss - ltp)
        reward = abs(ltp - target)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "SELL",
            "strategy": "PUT_RATIO_BACKSPREAD",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Put Ratio Backspread: {', '.join(reasons[:3])}{spread_info}",
        }
    except Exception as e:
        logger.error(f"Put Ratio Backspread error for {symbol}: {e}")
        return None


def analyze_long_straddle(symbol: str) -> Optional[dict]:
    """
    Long Straddle: Buy ATM Call + Buy ATM Put at same strike.

    Best when:
    - Expecting a big move but unsure of direction
    - Before major events (earnings, budget, RBI policy)
    - IV is low (cheap options) and expected to rise
    - Low ADX with potential for breakout

    Max Loss: Total premium paid (both call + put)
    Max Profit: Unlimited (either direction)
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
        adx = indicators.get("adx", 25)
        atr = indicators.get("atr", ltp * 0.02)
        bb_upper = indicators.get("bollinger_upper", ltp * 1.04)
        bb_lower = indicators.get("bollinger_lower", ltp * 0.96)
        rsi = indicators.get("rsi", 50)

        straddle_score = 0
        reasons = []

        # Low ADX = consolidation, potential breakout
        if adx < 20:
            straddle_score += 2
            reasons.append(f"ADX={adx} very low - breakout imminent")
        elif adx < 25:
            straddle_score += 1
            reasons.append(f"ADX={adx} consolidating")

        # Narrow Bollinger Bands = squeeze
        bb_width = (bb_upper - bb_lower) / ltp * 100
        if bb_width < 5:
            straddle_score += 2
            reasons.append(f"Bollinger squeeze ({bb_width:.1f}% width)")
        elif bb_width < 8:
            straddle_score += 1
            reasons.append(f"Narrow Bollinger ({bb_width:.1f}%)")

        # RSI near 50 = indecision
        if 45 < rsi < 55:
            straddle_score += 1
            reasons.append(f"RSI={rsi} neutral (indecision)")

        if straddle_score < 3:
            return None

        option_chain = get_option_chain(symbol)
        straddle_info = ""

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            if atm:
                call_premium = atm["call_ltp"]
                put_premium = atm["put_ltp"]
                total_premium = round(call_premium + put_premium, 2)
                upper_breakeven = round(atm["strike_price"] + total_premium, 2)
                lower_breakeven = round(atm["strike_price"] - total_premium, 2)

                iv = _estimate_option_iv(atm, "call")
                T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                call_greeks = calculate_all_greeks(
                    ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "call"
                )
                put_greeks = calculate_all_greeks(
                    ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "put"
                )
                net_delta = round(call_greeks["delta"] + put_greeks["delta"], 4)
                total_gamma = round(call_greeks["gamma"] + put_greeks["gamma"], 6)
                total_vega = round(call_greeks["vega"] + put_greeks["vega"], 4)
                total_theta = round(call_greeks["theta"] + put_greeks["theta"], 4)

                straddle_info = (
                    f" | Strike: {atm['strike_price']}, "
                    f"Call @{call_premium} + Put @{put_premium} = {total_premium}, "
                    f"Breakevens: {lower_breakeven}/{upper_breakeven}, "
                    f"Net Delta={net_delta}, Gamma={total_gamma}, "
                    f"Vega={total_vega}, Theta={total_theta}/day"
                )

        confidence = min(0.4 + straddle_score * 0.09, 0.85)
        target = round(ltp + 3 * atr, 2)
        stop_loss = round(ltp - 3 * atr, 2)

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "LONG_STRADDLE",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": 2.0,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Long Straddle: {', '.join(reasons[:3])}{straddle_info}",
        }
    except Exception as e:
        logger.error(f"Straddle error for {symbol}: {e}")
        return None


def analyze_long_strangle(symbol: str) -> Optional[dict]:
    """
    Long Strangle: Buy OTM Call + Buy OTM Put at different strikes.

    Best when:
    - Expecting a very big move in either direction
    - Cheaper than straddle (both options are OTM)
    - Before high-impact events
    - IV is low and expected to spike

    Max Loss: Total premium paid
    Max Profit: Unlimited (either direction)
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
        adx = indicators.get("adx", 25)
        atr = indicators.get("atr", ltp * 0.02)
        bb_upper = indicators.get("bollinger_upper", ltp * 1.04)
        bb_lower = indicators.get("bollinger_lower", ltp * 0.96)
        rsi = indicators.get("rsi", 50)

        strangle_score = 0
        reasons = []

        if adx < 18:
            strangle_score += 2
            reasons.append(f"ADX={adx} extremely low - big move expected")
        elif adx < 23:
            strangle_score += 1
            reasons.append(f"ADX={adx} low trend")

        bb_width = (bb_upper - bb_lower) / ltp * 100
        if bb_width < 4:
            strangle_score += 2
            reasons.append(f"Extreme Bollinger squeeze ({bb_width:.1f}%)")
        elif bb_width < 7:
            strangle_score += 1
            reasons.append(f"Tight range ({bb_width:.1f}%)")

        if 42 < rsi < 58:
            strangle_score += 1
            reasons.append(f"RSI={rsi} directionless")

        if strangle_score < 3:
            return None

        option_chain = get_option_chain(symbol)
        strangle_info = ""

        if option_chain:
            otm_call = _get_strike_by_offset(ltp, option_chain, 0.03)
            otm_put = _get_strike_by_offset(ltp, option_chain, -0.03)

            if otm_call and otm_put:
                call_premium = otm_call["call_ltp"]
                put_premium = otm_put["put_ltp"]
                total_premium = round(call_premium + put_premium, 2)
                upper_breakeven = round(otm_call["strike_price"] + total_premium, 2)
                lower_breakeven = round(otm_put["strike_price"] - total_premium, 2)

                strangle_info = (
                    f" | Buy {otm_call['strike_price']}CE @{call_premium} + "
                    f"Buy {otm_put['strike_price']}PE @{put_premium} = {total_premium}, "
                    f"Breakevens: {lower_breakeven}/{upper_breakeven}"
                )

        confidence = min(0.4 + strangle_score * 0.09, 0.83)
        target = round(ltp + 4 * atr, 2)
        stop_loss = round(ltp - 4 * atr, 2)

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "LONG_STRANGLE",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": 2.5,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Long Strangle: {', '.join(reasons[:3])}{strangle_info}",
        }
    except Exception as e:
        logger.error(f"Strangle error for {symbol}: {e}")
        return None
