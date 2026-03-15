"""
Options Analysis Router - Provides endpoints for options Greeks calculation,
options chain analytics, IV analysis, and options strategy recommendations.
"""

from fastapi import APIRouter, Query
from typing import Optional
from app.services.nse_data import get_stock_quote, get_option_chain
from app.services.options_greeks import (
    calculate_all_greeks,
    estimate_iv,
    calculate_pcr,
    calculate_max_pain,
    analyze_oi_buildup,
    analyze_iv_skew,
    calculate_iv_rank,
    calculate_moneyness,
    calculate_breakeven,
    black_scholes_price,
)

router = APIRouter(prefix="/api/options", tags=["Options Analysis"])


@router.get("/greeks/{symbol}")
async def get_greeks(
    symbol: str,
    strike: Optional[float] = Query(default=None, description="Strike price (defaults to ATM)"),
    option_type: str = Query(default="call", description="call or put"),
    days_to_expiry: int = Query(default=30, description="Days to expiration"),
    risk_free_rate: float = Query(default=0.065, description="Risk-free rate"),
):
    """Calculate all Greeks for a given option using Black-Scholes model."""
    quote = get_stock_quote(symbol.upper())
    if not quote:
        return {"error": f"Could not fetch data for {symbol}"}

    spot = quote["ltp"]

    if strike is None:
        option_chain = get_option_chain(symbol.upper())
        if option_chain:
            atm = min(option_chain, key=lambda x: abs(x["strike_price"] - spot))
            strike = atm["strike_price"]
        else:
            strike = round(spot / 50) * 50  # Round to nearest 50

    T = days_to_expiry / 365.0

    # Estimate IV from option chain if available
    sigma = 0.20  # default IV
    option_chain = get_option_chain(symbol.upper())
    if option_chain:
        for entry in option_chain:
            if abs(entry["strike_price"] - strike) < 1:
                iv_val = entry.get(f"{option_type}_iv")
                if iv_val and iv_val > 0:
                    sigma = iv_val / 100
                break

    greeks = calculate_all_greeks(spot, strike, T, risk_free_rate, sigma, option_type)
    greeks["symbol"] = symbol.upper()
    greeks["moneyness"] = calculate_moneyness(spot, strike, option_type)

    return greeks


@router.get("/chain-analytics/{symbol}")
async def get_chain_analytics(symbol: str):
    """
    Comprehensive options chain analytics including PCR, Max Pain,
    OI buildup, and IV skew analysis.
    """
    quote = get_stock_quote(symbol.upper())
    if not quote:
        return {"error": f"Could not fetch data for {symbol}"}

    option_chain = get_option_chain(symbol.upper())
    if not option_chain:
        return {"error": f"No option chain data for {symbol}", "data": {}}

    spot = quote["ltp"]

    pcr = calculate_pcr(option_chain)
    max_pain = calculate_max_pain(option_chain)
    oi_buildup = analyze_oi_buildup(option_chain, spot)
    iv_skew = analyze_iv_skew(option_chain, spot)

    return {
        "symbol": symbol.upper(),
        "spot_price": spot,
        "pcr": pcr,
        "max_pain": max_pain,
        "oi_buildup": oi_buildup,
        "iv_skew": iv_skew,
    }


@router.get("/price-calculator")
async def option_price_calculator(
    spot: float = Query(description="Spot/underlying price"),
    strike: float = Query(description="Strike price"),
    days_to_expiry: int = Query(default=30, description="Days to expiration"),
    iv: float = Query(default=20.0, description="Implied volatility in %"),
    option_type: str = Query(default="call", description="call or put"),
    risk_free_rate: float = Query(default=6.5, description="Risk-free rate in %"),
):
    """Calculate option price and all Greeks for given parameters."""
    T = days_to_expiry / 365.0
    sigma = iv / 100
    r = risk_free_rate / 100

    greeks = calculate_all_greeks(spot, strike, T, r, sigma, option_type)
    greeks["moneyness"] = calculate_moneyness(spot, strike, option_type)
    greeks["breakeven"] = calculate_breakeven(greeks["price"], strike, option_type)

    return greeks


@router.get("/pcr/{symbol}")
async def get_pcr(symbol: str):
    """Get Put-Call Ratio analysis for a symbol."""
    option_chain = get_option_chain(symbol.upper())
    if not option_chain:
        return {"error": f"No option chain data for {symbol}"}

    pcr = calculate_pcr(option_chain)
    pcr["symbol"] = symbol.upper()
    return pcr


@router.get("/max-pain/{symbol}")
async def get_max_pain(symbol: str):
    """Get Max Pain strike price for a symbol."""
    quote = get_stock_quote(symbol.upper())
    option_chain = get_option_chain(symbol.upper())

    if not option_chain:
        return {"error": f"No option chain data for {symbol}"}

    max_pain = calculate_max_pain(option_chain)
    spot = quote["ltp"] if quote else 0

    distance_pct = abs(spot - max_pain) / spot * 100 if spot > 0 else 0
    direction = "above" if spot > max_pain else "below"

    return {
        "symbol": symbol.upper(),
        "max_pain": max_pain,
        "spot_price": spot,
        "distance_percent": round(distance_pct, 2),
        "spot_vs_max_pain": direction,
        "interpretation": f"Price is {distance_pct:.1f}% {direction} Max Pain. "
                         f"Near expiry, price tends to gravitate toward {max_pain}.",
    }


@router.get("/iv-analysis/{symbol}")
async def get_iv_analysis(symbol: str):
    """Get comprehensive IV analysis including skew, HV comparison, etc."""
    quote = get_stock_quote(symbol.upper())
    option_chain = get_option_chain(symbol.upper())

    if not quote or not option_chain:
        return {"error": f"Could not fetch data for {symbol}"}

    spot = quote["ltp"]
    iv_skew = analyze_iv_skew(option_chain, spot)

    # Collect all IVs from chain
    all_ivs = []
    for entry in option_chain:
        if entry.get("call_iv"):
            all_ivs.append(entry["call_iv"])
        if entry.get("put_iv"):
            all_ivs.append(entry["put_iv"])

    avg_iv = round(sum(all_ivs) / len(all_ivs), 2) if all_ivs else 0
    max_iv = max(all_ivs) if all_ivs else 0
    min_iv = min(all_ivs) if all_ivs else 0

    return {
        "symbol": symbol.upper(),
        "spot_price": spot,
        "iv_skew": iv_skew,
        "average_chain_iv": avg_iv,
        "max_iv": max_iv,
        "min_iv": min_iv,
        "iv_spread": round(max_iv - min_iv, 2),
    }


@router.get("/oi-analysis/{symbol}")
async def get_oi_analysis(symbol: str):
    """Get detailed Open Interest analysis for support/resistance levels."""
    quote = get_stock_quote(symbol.upper())
    option_chain = get_option_chain(symbol.upper())

    if not quote or not option_chain:
        return {"error": f"Could not fetch data for {symbol}"}

    spot = quote["ltp"]
    oi_data = analyze_oi_buildup(option_chain, spot)
    pcr = calculate_pcr(option_chain)

    # Top 5 strikes by call OI and put OI
    top_call_oi = sorted(option_chain, key=lambda x: x.get("call_oi", 0), reverse=True)[:5]
    top_put_oi = sorted(option_chain, key=lambda x: x.get("put_oi", 0), reverse=True)[:5]

    return {
        "symbol": symbol.upper(),
        "spot_price": spot,
        "oi_buildup": oi_data,
        "pcr": pcr,
        "top_call_oi_strikes": [
            {"strike": e["strike_price"], "call_oi": e.get("call_oi", 0)}
            for e in top_call_oi
        ],
        "top_put_oi_strikes": [
            {"strike": e["strike_price"], "put_oi": e.get("put_oi", 0)}
            for e in top_put_oi
        ],
    }
