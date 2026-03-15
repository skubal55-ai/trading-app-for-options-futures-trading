"""
Options Greeks Calculator using Black-Scholes Model.

Calculates Delta, Gamma, Theta, Vega, Rho for European-style options.
Also includes IV estimation, option pricing, and Greeks-based analytics.

References:
- Black, F. & Scholes, M. (1973) "The Pricing of Options and Corporate Liabilities"
- Hull, J.C. "Options, Futures, and Other Derivatives"
- Natenberg, S. "Option Volatility and Pricing"
"""

import math
import numpy as np
from typing import Optional
from scipy.stats import norm
import logging

logger = logging.getLogger(__name__)


def black_scholes_price(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    """
    Calculate Black-Scholes option price.

    Args:
        S: Current stock/underlying price
        K: Strike price
        T: Time to expiration in years
        r: Risk-free interest rate (annualized)
        sigma: Implied volatility (annualized)
        option_type: 'call' or 'put'

    Returns:
        Option price
    """
    if T <= 0 or sigma <= 0:
        if option_type == "call":
            return max(S - K, 0)
        return max(K - S, 0)

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return round(price, 2)


def calculate_delta(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    """
    Delta: Rate of change of option price with respect to underlying price.
    Call delta: 0 to 1, Put delta: -1 to 0.
    """
    if T <= 0 or sigma <= 0:
        if option_type == "call":
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))

    if option_type == "call":
        return round(norm.cdf(d1), 4)
    return round(norm.cdf(d1) - 1, 4)


def calculate_gamma(
    S: float, K: float, T: float, r: float, sigma: float
) -> float:
    """
    Gamma: Rate of change of delta with respect to underlying price.
    Same for calls and puts. Highest for ATM options near expiry.
    """
    if T <= 0 or sigma <= 0:
        return 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return round(norm.pdf(d1) / (S * sigma * math.sqrt(T)), 6)


def calculate_theta(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    """
    Theta: Rate of change of option price with respect to time (time decay).
    Returned as daily theta (per calendar day). Usually negative for long options.
    """
    if T <= 0 or sigma <= 0:
        return 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    common_term = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))

    if option_type == "call":
        theta = common_term - r * K * math.exp(-r * T) * norm.cdf(d2)
    else:
        theta = common_term + r * K * math.exp(-r * T) * norm.cdf(-d2)

    return round(theta / 365, 4)


def calculate_vega(
    S: float, K: float, T: float, r: float, sigma: float
) -> float:
    """
    Vega: Rate of change of option price with respect to volatility.
    Same for calls and puts. Returns change per 1% move in IV.
    """
    if T <= 0 or sigma <= 0:
        return 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return round(S * norm.pdf(d1) * math.sqrt(T) / 100, 4)


def calculate_rho(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    """
    Rho: Rate of change of option price with respect to interest rate.
    Returns change per 1% move in interest rate.
    """
    if T <= 0 or sigma <= 0:
        return 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        return round(K * T * math.exp(-r * T) * norm.cdf(d2) / 100, 4)
    return round(-K * T * math.exp(-r * T) * norm.cdf(-d2) / 100, 4)


def calculate_all_greeks(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> dict:
    """Calculate all Greeks for a given option."""
    return {
        "price": black_scholes_price(S, K, T, r, sigma, option_type),
        "delta": calculate_delta(S, K, T, r, sigma, option_type),
        "gamma": calculate_gamma(S, K, T, r, sigma),
        "theta": calculate_theta(S, K, T, r, sigma, option_type),
        "vega": calculate_vega(S, K, T, r, sigma),
        "rho": calculate_rho(S, K, T, r, sigma, option_type),
        "option_type": option_type,
        "spot": S,
        "strike": K,
        "time_to_expiry": round(T, 4),
        "iv": round(sigma * 100, 2),
        "risk_free_rate": round(r * 100, 2),
    }


def estimate_iv(
    market_price: float, S: float, K: float, T: float, r: float,
    option_type: str = "call", precision: float = 0.0001, max_iter: int = 100
) -> float:
    """
    Estimate implied volatility using Newton-Raphson method.

    Args:
        market_price: Current market price of the option
        S: Underlying price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        option_type: 'call' or 'put'

    Returns:
        Estimated implied volatility (annualized, as decimal e.g. 0.20 = 20%)
    """
    if T <= 0:
        return 0.0

    sigma = 0.3  # Initial guess

    for _ in range(max_iter):
        price = black_scholes_price(S, K, T, r, sigma, option_type)
        vega_val = calculate_vega(S, K, T, r, sigma) * 100  # un-scale vega

        if abs(vega_val) < 1e-10:
            break

        diff = market_price - price
        if abs(diff) < precision:
            break

        sigma += diff / vega_val
        sigma = max(sigma, 0.01)
        sigma = min(sigma, 5.0)

    return round(sigma, 4)


def calculate_iv_percentile(iv_history: list[float], current_iv: float) -> float:
    """
    Calculate IV Percentile: % of days in the past year where IV was lower than current IV.
    High IV percentile (>50) suggests selling strategies; low suggests buying strategies.
    """
    if not iv_history:
        return 50.0
    count_lower = sum(1 for iv in iv_history if iv < current_iv)
    return round((count_lower / len(iv_history)) * 100, 2)


def calculate_iv_rank(iv_history: list[float], current_iv: float) -> float:
    """
    IV Rank = (Current IV - 52wk Low IV) / (52wk High IV - 52wk Low IV) * 100
    """
    if not iv_history:
        return 50.0
    min_iv = min(iv_history)
    max_iv = max(iv_history)
    if max_iv == min_iv:
        return 50.0
    return round(((current_iv - min_iv) / (max_iv - min_iv)) * 100, 2)


def calculate_moneyness(S: float, K: float, option_type: str = "call") -> str:
    """Determine if an option is ITM, ATM, or OTM."""
    ratio = S / K
    if option_type == "call":
        if ratio > 1.02:
            return "ITM"
        elif ratio < 0.98:
            return "OTM"
        return "ATM"
    else:
        if ratio < 0.98:
            return "ITM"
        elif ratio > 1.02:
            return "OTM"
        return "ATM"


def calculate_breakeven(
    premium: float, strike: float, option_type: str = "call"
) -> float:
    """Calculate breakeven price for an option position."""
    if option_type == "call":
        return round(strike + premium, 2)
    return round(strike - premium, 2)


def calculate_max_pain(option_chain: list[dict]) -> float:
    """
    Calculate Max Pain: The strike price at which option writers would suffer minimum losses.
    Based on the theory that option prices tend to gravitate toward max pain at expiry.
    """
    if not option_chain:
        return 0.0

    strikes = [entry["strike_price"] for entry in option_chain]
    min_pain = float("inf")
    max_pain_strike = strikes[0]

    for test_strike in strikes:
        total_pain = 0.0
        for entry in option_chain:
            call_oi = entry.get("call_oi", 0)
            put_oi = entry.get("put_oi", 0)
            strike = entry["strike_price"]

            # Call pain: if expiry price > strike, call writers lose
            if test_strike > strike:
                total_pain += (test_strike - strike) * call_oi

            # Put pain: if expiry price < strike, put writers lose
            if test_strike < strike:
                total_pain += (strike - test_strike) * put_oi

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = test_strike

    return max_pain_strike


def calculate_pcr(option_chain: list[dict]) -> dict:
    """
    Calculate Put-Call Ratio from option chain data.
    PCR > 1: Bearish sentiment (more puts being bought)
    PCR < 1: Bullish sentiment (more calls being bought)
    PCR around 0.7-1.0: Neutral / normal range
    """
    total_call_oi = sum(entry.get("call_oi", 0) for entry in option_chain)
    total_put_oi = sum(entry.get("put_oi", 0) for entry in option_chain)
    total_call_volume = sum(entry.get("call_volume", 0) for entry in option_chain)
    total_put_volume = sum(entry.get("put_volume", 0) for entry in option_chain)

    pcr_oi = round(total_put_oi / total_call_oi, 4) if total_call_oi > 0 else 0
    pcr_volume = round(total_put_volume / total_call_volume, 4) if total_call_volume > 0 else 0

    sentiment = "NEUTRAL"
    if pcr_oi > 1.2:
        sentiment = "VERY_BEARISH"
    elif pcr_oi > 1.0:
        sentiment = "BEARISH"
    elif pcr_oi < 0.5:
        sentiment = "VERY_BULLISH"
    elif pcr_oi < 0.7:
        sentiment = "BULLISH"

    return {
        "pcr_oi": pcr_oi,
        "pcr_volume": pcr_volume,
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
        "total_call_volume": total_call_volume,
        "total_put_volume": total_put_volume,
        "sentiment": sentiment,
    }


def analyze_oi_buildup(option_chain: list[dict], spot_price: float) -> dict:
    """
    Analyze OI buildup around current price to identify support/resistance.
    High Call OI = Resistance level (writers expect price won't go above)
    High Put OI = Support level (writers expect price won't go below)
    """
    if not option_chain:
        return {}

    max_call_oi_strike = max(option_chain, key=lambda x: x.get("call_oi", 0))
    max_put_oi_strike = max(option_chain, key=lambda x: x.get("put_oi", 0))

    # Find immediate support and resistance from OI
    atm_strikes = sorted(option_chain, key=lambda x: abs(x["strike_price"] - spot_price))[:5]

    immediate_resistance = None
    immediate_support = None
    for entry in sorted(atm_strikes, key=lambda x: x["strike_price"]):
        if entry["strike_price"] >= spot_price and entry.get("call_oi", 0) > 0:
            if immediate_resistance is None:
                immediate_resistance = entry["strike_price"]
        if entry["strike_price"] <= spot_price and entry.get("put_oi", 0) > 0:
            immediate_support = entry["strike_price"]

    return {
        "max_call_oi_strike": max_call_oi_strike["strike_price"],
        "max_call_oi": max_call_oi_strike.get("call_oi", 0),
        "max_put_oi_strike": max_put_oi_strike["strike_price"],
        "max_put_oi": max_put_oi_strike.get("put_oi", 0),
        "resistance_from_oi": immediate_resistance or max_call_oi_strike["strike_price"],
        "support_from_oi": immediate_support or max_put_oi_strike["strike_price"],
        "spot_price": spot_price,
    }


def analyze_iv_skew(option_chain: list[dict], spot_price: float) -> dict:
    """
    Analyze IV skew across strikes.
    Normal skew: OTM puts have higher IV than OTM calls (volatility smile)
    Reverse skew: OTM calls have higher IV (unusual, potential squeeze)
    """
    if not option_chain:
        return {}

    otm_puts = []
    otm_calls = []
    atm_iv = None

    for entry in option_chain:
        strike = entry["strike_price"]
        if abs(strike - spot_price) / spot_price < 0.02:
            call_iv = entry.get("call_iv")
            put_iv = entry.get("put_iv")
            if call_iv and put_iv:
                atm_iv = (call_iv + put_iv) / 2
        elif strike < spot_price and entry.get("put_iv"):
            otm_puts.append({"strike": strike, "iv": entry["put_iv"]})
        elif strike > spot_price and entry.get("call_iv"):
            otm_calls.append({"strike": strike, "iv": entry["call_iv"]})

    avg_otm_put_iv = np.mean([p["iv"] for p in otm_puts]) if otm_puts else 0
    avg_otm_call_iv = np.mean([c["iv"] for c in otm_calls]) if otm_calls else 0

    skew_type = "NORMAL"
    if avg_otm_put_iv > 0 and avg_otm_call_iv > 0:
        skew_ratio = avg_otm_put_iv / avg_otm_call_iv
        if skew_ratio > 1.15:
            skew_type = "STEEP_PUT_SKEW"
        elif skew_ratio > 1.05:
            skew_type = "NORMAL"
        elif skew_ratio < 0.95:
            skew_type = "REVERSE_SKEW"
        else:
            skew_type = "FLAT"
    else:
        skew_ratio = 1.0

    return {
        "atm_iv": round(atm_iv, 2) if atm_iv else None,
        "avg_otm_put_iv": round(avg_otm_put_iv, 2),
        "avg_otm_call_iv": round(avg_otm_call_iv, 2),
        "skew_ratio": round(skew_ratio, 4),
        "skew_type": skew_type,
        "interpretation": _interpret_skew(skew_type),
    }


def _interpret_skew(skew_type: str) -> str:
    interpretations = {
        "STEEP_PUT_SKEW": "High demand for downside protection - institutions hedging, consider selling OTM puts or buying put spreads",
        "NORMAL": "Normal market conditions - standard volatility smile",
        "REVERSE_SKEW": "Unusual upside demand - potential short squeeze or breakout expected, consider call strategies",
        "FLAT": "Low skew - market uncertain about direction, consider straddle/strangle strategies",
    }
    return interpretations.get(skew_type, "")
