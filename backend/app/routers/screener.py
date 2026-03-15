from fastapi import APIRouter, Query
from typing import Optional
from app.services.strategy_engine import run_screener, STRATEGY_ANALYZERS
from app.services.nse_data import NIFTY50_STOCKS

router = APIRouter(prefix="/api/screener", tags=["Screener"])


@router.get("/scan")
async def scan_stocks(
    strategies: Optional[str] = Query(default=None, description="Comma-separated strategy names"),
    signal: Optional[str] = Query(default=None, description="BUY or SELL filter"),
    symbols: Optional[str] = Query(default=None, description="Comma-separated symbols, defaults to NIFTY50"),
    limit: int = Query(default=20, description="Max results"),
):
    symbol_list = symbols.split(",") if symbols else NIFTY50_STOCKS[:15]
    strategy_list = strategies.split(",") if strategies else None

    results = run_screener(
        symbols=symbol_list,
        strategies=strategy_list,
        signal_filter=signal,
    )

    return {"results": results[:limit], "total": len(results)}


@router.get("/strategies")
async def available_strategies():
    return {
        "strategies": [
            # --- Equity Strategies ---
            {
                "id": "MA_CROSSOVER",
                "name": "Moving Average Crossover",
                "description": "EMA 9/21 crossover with SMA 50 trend confirmation",
                "type": "Trend Following",
                "segment": "EQUITY",
            },
            {
                "id": "RSI_DIVERGENCE",
                "name": "RSI Divergence",
                "description": "RSI oversold/overbought signals with MACD confirmation",
                "type": "Mean Reversion",
                "segment": "EQUITY",
            },
            {
                "id": "MACD_SIGNAL",
                "name": "MACD Signal",
                "description": "MACD line crossover with signal line confirmation",
                "type": "Momentum",
                "segment": "EQUITY",
            },
            {
                "id": "FIBONACCI_RETRACEMENT",
                "name": "Fibonacci Retracement",
                "description": "Price action at key Fibonacci levels (38.2%, 50%, 61.8%)",
                "type": "Support/Resistance",
                "segment": "EQUITY",
            },
            {
                "id": "BOLLINGER_BREAKOUT",
                "name": "Bollinger Band Breakout",
                "description": "Price touching or breaking Bollinger Bands for reversal signals",
                "type": "Volatility",
                "segment": "EQUITY",
            },
            {
                "id": "SUPERTREND",
                "name": "Supertrend",
                "description": "Supertrend indicator for trend direction and entry points",
                "type": "Trend Following",
                "segment": "EQUITY",
            },
            {
                "id": "VWAP_STRATEGY",
                "name": "VWAP Strategy",
                "description": "Volume Weighted Average Price for intraday support/resistance",
                "type": "Intraday",
                "segment": "EQUITY",
            },
            {
                "id": "ORDER_BLOCK",
                "name": "Order Block (SMC)",
                "description": "Smart Money Concept - institutional order blocks with volume confirmation",
                "type": "Institutional",
                "segment": "EQUITY",
            },
            {
                "id": "SUPPLY_DEMAND",
                "name": "Supply & Demand Zones",
                "description": "Identifies institutional accumulation and distribution zones",
                "type": "Institutional",
                "segment": "EQUITY",
            },
            {
                "id": "EMA_RIBBON",
                "name": "EMA Ribbon",
                "description": "Multi-EMA (8,13,21,34,55) alignment for strong trend confirmation",
                "type": "Trend Following",
                "segment": "EQUITY",
            },
            {
                "id": "VOLUME_BREAKOUT",
                "name": "Volume Breakout",
                "description": "Breakouts with 2x+ average volume - institutional participation",
                "type": "Breakout",
                "segment": "EQUITY",
            },
            {
                "id": "ICT_FVG",
                "name": "ICT Fair Value Gap",
                "description": "Inner Circle Trader concept - price gaps indicating smart money activity",
                "type": "Smart Money",
                "segment": "EQUITY",
            },
            {
                "id": "ORB_STRATEGY",
                "name": "Opening Range Breakout",
                "description": "15-minute opening range breakout/breakdown for intraday trading",
                "type": "Intraday",
                "segment": "EQUITY",
            },
            # --- Call-Side Options Buying Strategies ---
            {
                "id": "LONG_CALL",
                "name": "Long Call",
                "description": "Buy ATM/ITM call for directional bullish bet. Uses delta, gamma, PCR and max pain analysis. Best when IV is low.",
                "type": "Options - Call Side",
                "segment": "OPTIONS",
            },
            {
                "id": "BULL_CALL_SPREAD",
                "name": "Bull Call Spread",
                "description": "Buy ATM call + Sell OTM call. Defined risk bullish strategy with lower cost. Includes net delta/theta calculation.",
                "type": "Options - Call Side",
                "segment": "OPTIONS",
            },
            {
                "id": "LONG_CALL_BUTTERFLY",
                "name": "Long Call Butterfly",
                "description": "Buy 1 ITM + Sell 2 ATM + Buy 1 OTM call. Low cost range-bound strategy. Best when ADX < 25 and IV is low.",
                "type": "Options - Call Side",
                "segment": "OPTIONS",
            },
            {
                "id": "CALL_RATIO_BACKSPREAD",
                "name": "Call Ratio Backspread",
                "description": "Sell 1 ATM call + Buy 2 OTM calls. Unlimited upside with limited risk. Benefits from IV expansion. Best before breakouts.",
                "type": "Options - Call Side",
                "segment": "OPTIONS",
            },
            {
                "id": "LONG_CALL_CONDOR",
                "name": "Long Call Condor",
                "description": "4-leg call spread for wider profit zone than butterfly. Best in non-trending markets with low IV.",
                "type": "Options - Call Side",
                "segment": "OPTIONS",
            },
            # --- Put-Side Options Buying Strategies ---
            {
                "id": "LONG_PUT",
                "name": "Long Put",
                "description": "Buy ATM put for directional bearish bet. Uses delta, gamma and options chain analysis. Best when bearish signals align.",
                "type": "Options - Put Side",
                "segment": "OPTIONS",
            },
            {
                "id": "BEAR_PUT_SPREAD",
                "name": "Bear Put Spread",
                "description": "Buy ATM put + Sell OTM put. Defined risk bearish strategy with net delta analysis. Lower cost than naked put.",
                "type": "Options - Put Side",
                "segment": "OPTIONS",
            },
            {
                "id": "LONG_PUT_BUTTERFLY",
                "name": "Long Put Butterfly",
                "description": "Buy 1 ITM + Sell 2 ATM + Buy 1 OTM put. Range-bound with slight bearish bias. Low cost, high R:R.",
                "type": "Options - Put Side",
                "segment": "OPTIONS",
            },
            {
                "id": "PUT_RATIO_BACKSPREAD",
                "name": "Put Ratio Backspread",
                "description": "Sell 1 ATM put + Buy 2 OTM puts. Crash protection with unlimited downside profit. Great for black swan events.",
                "type": "Options - Put Side",
                "segment": "OPTIONS",
            },
            # --- Volatility Options Strategies ---
            {
                "id": "LONG_STRADDLE",
                "name": "Long Straddle",
                "description": "Buy ATM Call + ATM Put. Profits from big move in either direction. Full Greeks analysis with breakeven levels. Best when IV is low and ADX < 20.",
                "type": "Options - Volatility",
                "segment": "OPTIONS",
            },
            {
                "id": "LONG_STRANGLE",
                "name": "Long Strangle",
                "description": "Buy OTM Call + OTM Put. Cheaper than straddle, needs bigger move. Best before high-impact events with Bollinger squeeze.",
                "type": "Options - Volatility",
                "segment": "OPTIONS",
            },
            # --- Stock + Options Combined Strategies ---
            {
                "id": "COVERED_CALL",
                "name": "Covered Call",
                "description": "Long stock + Sell OTM call for income generation. Shows yield%, annualized return, short delta and theta income. Best when mildly bullish.",
                "type": "Stock Options",
                "segment": "OPTIONS",
            },
            {
                "id": "PROTECTIVE_PUT",
                "name": "Protective Put (Married Put)",
                "description": "Long stock + Buy OTM put for portfolio insurance. Calculates cost%, floor price, and uses OI support analysis. Best before events.",
                "type": "Stock Options",
                "segment": "OPTIONS",
            },
            {
                "id": "COLLAR",
                "name": "Collar Strategy",
                "description": "Long stock + Buy put + Sell call. Zero/low cost hedge with defined range. Shows max profit/loss and net cost. Best for concentrated positions.",
                "type": "Stock Options",
                "segment": "OPTIONS",
            },
            {
                "id": "SYNTHETIC_LONG",
                "name": "Synthetic Long Stock",
                "description": "Buy ATM call + Sell ATM put. Stock-like exposure with less capital. Net delta ~1.0. Best when strongly bullish with limited capital.",
                "type": "Stock Options",
                "segment": "OPTIONS",
            },
            {
                "id": "SYNTHETIC_SHORT",
                "name": "Synthetic Short Stock",
                "description": "Buy ATM put + Sell ATM call. Short-stock exposure without borrowing. Net delta ~-1.0. Best when strongly bearish.",
                "type": "Stock Options",
                "segment": "OPTIONS",
            },
            {
                "id": "STOCK_REPAIR",
                "name": "Stock Repair Strategy",
                "description": "For losing stocks: Buy 1 ATM call + Sell 2 OTM calls. Doubles recovery rate at zero/low cost. Best when stock down 10-30%.",
                "type": "Stock Options",
                "segment": "OPTIONS",
            },
            {
                "id": "DELTA_NEUTRAL_HEDGE",
                "name": "Delta-Neutral Hedge",
                "description": "Long stock + Buy puts for delta-neutral position. Profits from gamma (big moves). Uses hedge ratio calculation. Best before volatility events.",
                "type": "Stock Options",
                "segment": "OPTIONS",
            },
            # --- Greeks-Based Strategies ---
            {
                "id": "DELTA_DIRECTIONAL",
                "name": "Delta Directional",
                "description": "Select options by target delta (0.65) for optimal probability/leverage. Full Greeks analysis with strike selection. Uses ADX for trend strength.",
                "type": "Greeks-Based",
                "segment": "OPTIONS",
            },
            {
                "id": "GAMMA_SCALPING",
                "name": "Gamma Scalping",
                "description": "Exploit high gamma near expiry for quick profits. ATM weekly options with gamma/theta ratio analysis. Best for intraday scalps.",
                "type": "Greeks-Based",
                "segment": "OPTIONS",
            },
            {
                "id": "IV_CRUSH_PLAY",
                "name": "IV Crush Play",
                "description": "Position for post-event IV collapse. Compares IV vs HV, uses IV/HV ratio. Sell strangles or credit spreads when IV is elevated.",
                "type": "Greeks-Based",
                "segment": "OPTIONS",
            },
            {
                "id": "IV_EXPANSION_PLAY",
                "name": "IV Expansion Play",
                "description": "Buy cheap options when IV is low, expecting rise. Uses Bollinger squeeze + low ADX as catalysts. Long vega position.",
                "type": "Greeks-Based",
                "segment": "OPTIONS",
            },
            {
                "id": "OI_BREAKOUT",
                "name": "OI-Based Breakout",
                "description": "Uses options chain OI to predict breakout levels. Max Call OI = resistance, Max Put OI = support. Includes PCR and Max Pain confirmation.",
                "type": "Options Chain",
                "segment": "OPTIONS",
            },
            {
                "id": "PCR_REVERSAL",
                "name": "PCR Reversal (Contrarian)",
                "description": "Contrarian signals from extreme Put-Call Ratio. PCR > 1.5 = contrarian BUY, PCR < 0.5 = contrarian SELL. Uses RSI for confirmation.",
                "type": "Options Chain",
                "segment": "OPTIONS",
            },
            {
                "id": "MAX_PAIN_MAGNET",
                "name": "Max Pain Magnet",
                "description": "Trade toward max pain level near expiry. Options prices gravitate toward max pain where writers suffer least. PCR-confirmed mean reversion.",
                "type": "Options Chain",
                "segment": "OPTIONS",
            },
            {
                "id": "GEX_STRATEGY",
                "name": "Gamma Exposure (GEX)",
                "description": "Trade based on market maker hedging flows. Positive GEX = mean-reverting (sell rips/buy dips). Negative GEX = trending (follow momentum).",
                "type": "Greeks-Based",
                "segment": "OPTIONS",
            },
        ]
    }



@router.get("/quick-scan/{strategy}")
async def quick_scan(
    strategy: str,
    signal: Optional[str] = Query(default=None),
    limit: int = Query(default=10),
):
    results = run_screener(
        symbols=NIFTY50_STOCKS[:15],
        strategies=[strategy.upper()],
        signal_filter=signal,
    )
    return {"strategy": strategy.upper(), "results": results[:limit]}
