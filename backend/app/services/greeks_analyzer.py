"""
Greeks-Based Signal Generation Strategies.

These strategies use options Greeks and options chain analytics to generate
trading signals. They analyze delta exposure, gamma opportunities, IV crush/expansion,
theta decay patterns, and vega plays.

Strategies:
- Delta Directional: High delta options for directional conviction
- Gamma Scalping: Exploit high gamma near expiry for quick moves
- IV Crush Play: Trade around events where IV is expected to collapse
- IV Expansion Play: Position before events where IV is expected to spike
- Theta Decay Harvester: Sell overpriced near-expiry options
- Vega Play: Trade IV mean reversion
- OI-Based Breakout: Use options chain OI to predict breakout levels
- PCR Reversal: Use extreme PCR for contrarian signals
- Max Pain Magnet: Trade toward max pain level near expiry
- Gamma Exposure (GEX) Strategy: Market maker hedging flows

References:
- Passarelli, D. "Trading Option Greeks"
- Sinclair, E. "Option Trading: Pricing and Volatility Strategies"
- Natenberg, S. "Option Volatility and Pricing"
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
    calculate_iv_rank,
)
import logging

logger = logging.getLogger(__name__)

DEFAULT_RISK_FREE_RATE = 0.065
DEFAULT_WEEKLY_EXPIRY_DAYS = 7
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


def analyze_delta_directional(symbol: str) -> Optional[dict]:
    """
    Delta Directional Strategy: Use high-delta options for directional trades.

    Selects options with delta > 0.7 (deep ITM) for high probability or
    delta 0.4-0.6 (ATM) for best risk/reward.

    Entry criteria:
    - Strong directional signal from technicals
    - Select strike based on delta preference
    - Consider gamma for acceleration potential
    - Check theta to ensure time decay doesn't eat profits

    Best for: Traders who want option leverage with high probability
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
        adx = indicators.get("adx", 20)

        # Determine direction
        direction = None
        dir_score = 0
        reasons = []

        if ema_9 > ema_21 and ltp > ema_9:
            dir_score += 1
            direction = "BULLISH"
        elif ema_9 < ema_21 and ltp < ema_9:
            dir_score += 1
            direction = "BEARISH"

        if supertrend_dir == "UP" and direction == "BULLISH":
            dir_score += 1
        elif supertrend_dir == "DOWN" and direction == "BEARISH":
            dir_score += 1

        if adx > 25:
            dir_score += 1
            reasons.append(f"ADX={adx} strong trend")

        if indicators.get("macd_histogram", 0) > 0 and direction == "BULLISH":
            dir_score += 1
        elif indicators.get("macd_histogram", 0) < 0 and direction == "BEARISH":
            dir_score += 1

        if dir_score < 3 or direction is None:
            return None

        option_chain = get_option_chain(symbol)
        greeks_info = ""

        if option_chain:
            if direction == "BULLISH":
                # Find call with delta ~0.65 for good probability + leverage
                best_strike = None
                best_delta_diff = float("inf")
                target_delta = 0.65

                for entry in option_chain:
                    iv = _estimate_option_iv(entry, "call")
                    T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                    greeks = calculate_all_greeks(
                        ltp, entry["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "call"
                    )
                    delta_diff = abs(greeks["delta"] - target_delta)
                    if delta_diff < best_delta_diff:
                        best_delta_diff = delta_diff
                        best_strike = entry
                        best_greeks = greeks

                if best_strike:
                    reasons.append(f"Delta={best_greeks['delta']} high-probability call")
                    reasons.append(f"Gamma={best_greeks['gamma']} (acceleration)")
                    greeks_info = (
                        f" | Buy {best_strike['strike_price']}CE @{best_strike['call_ltp']}, "
                        f"Delta={best_greeks['delta']}, Gamma={best_greeks['gamma']}, "
                        f"Theta={best_greeks['theta']}/day, Vega={best_greeks['vega']}"
                    )
            else:
                # Find put with delta ~-0.65
                best_strike = None
                best_delta_diff = float("inf")
                target_delta = -0.65

                for entry in option_chain:
                    iv = _estimate_option_iv(entry, "put")
                    T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
                    greeks = calculate_all_greeks(
                        ltp, entry["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, "put"
                    )
                    delta_diff = abs(greeks["delta"] - target_delta)
                    if delta_diff < best_delta_diff:
                        best_delta_diff = delta_diff
                        best_strike = entry
                        best_greeks = greeks

                if best_strike:
                    reasons.append(f"Delta={best_greeks['delta']} high-probability put")
                    reasons.append(f"Gamma={best_greeks['gamma']}")
                    greeks_info = (
                        f" | Buy {best_strike['strike_price']}PE @{best_strike['put_ltp']}, "
                        f"Delta={best_greeks['delta']}, Gamma={best_greeks['gamma']}, "
                        f"Theta={best_greeks['theta']}/day, Vega={best_greeks['vega']}"
                    )

        signal = "BUY" if direction == "BULLISH" else "SELL"
        confidence = min(0.5 + dir_score * 0.08, 0.90)

        if signal == "BUY":
            target = round(ltp + 3 * atr, 2)
            stop_loss = round(ltp - 1.5 * atr, 2)
        else:
            target = round(ltp - 3 * atr, 2)
            stop_loss = round(ltp + 1.5 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "DELTA_DIRECTIONAL",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Delta Directional ({direction}): {', '.join(reasons[:3])}{greeks_info}",
        }
    except Exception as e:
        logger.error(f"Delta Directional error for {symbol}: {e}")
        return None


def analyze_gamma_scalping(symbol: str) -> Optional[dict]:
    """
    Gamma Scalping Strategy: Exploit high gamma near expiry for quick profits.

    High gamma means delta changes rapidly with price - ideal for scalping.
    ATM options near expiry have the highest gamma.

    Entry criteria:
    - Near weekly/monthly expiry (high gamma)
    - ATM options preferred (highest gamma)
    - Low theta relative to gamma (gamma/theta ratio)
    - Intraday momentum signal

    Best for: Quick intraday/1-2 day trades near expiry
    """
    try:
        data = get_historical_data(symbol, period="1mo", interval="1d")
        if data is None or len(data) < 10:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None

        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.02)
        rsi = indicators.get("rsi", 50)

        score = 0
        reasons = []

        # Need intraday momentum for gamma scalping
        if rsi > 55 or rsi < 45:
            score += 1
            reasons.append(f"RSI={rsi} momentum present")

        # Recent price action showing movement potential
        closes = data["Close"].values
        if len(closes) >= 5:
            recent_range = (max(closes[-5:]) - min(closes[-5:])) / ltp * 100
            if recent_range > 2:
                score += 1
                reasons.append(f"Recent range={recent_range:.1f}% (active)")

        if indicators.get("macd_histogram", 0) != 0:
            score += 1
            reasons.append("MACD showing momentum")

        if score < 2:
            return None

        option_chain = get_option_chain(symbol)
        gamma_info = ""
        signal = "BUY" if rsi > 50 else "SELL"

        if option_chain:
            atm = _get_atm_strike(ltp, option_chain)
            if atm:
                iv = _estimate_option_iv(atm, "call" if signal == "BUY" else "put")
                # Use short expiry for high gamma
                T = _days_to_years(DEFAULT_WEEKLY_EXPIRY_DAYS)
                opt_type = "call" if signal == "BUY" else "put"
                greeks = calculate_all_greeks(
                    ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, iv, opt_type
                )

                gamma_theta_ratio = abs(greeks["gamma"] / greeks["theta"]) if greeks["theta"] != 0 else 0

                reasons.append(f"Gamma={greeks['gamma']} (high near expiry)")
                if gamma_theta_ratio > 0.01:
                    score += 1
                    reasons.append(f"Gamma/Theta ratio={gamma_theta_ratio:.4f} favorable")

                premium = atm["call_ltp"] if signal == "BUY" else atm["put_ltp"]
                gamma_info = (
                    f" | ATM {atm['strike_price']}{'CE' if signal == 'BUY' else 'PE'} "
                    f"@{premium}, Gamma={greeks['gamma']}, "
                    f"Delta={greeks['delta']}, Theta={greeks['theta']}/day, "
                    f"Weekly expiry - high gamma scalp"
                )

        confidence = min(0.45 + score * 0.09, 0.82)

        if signal == "BUY":
            target = round(ltp + 1.5 * atr, 2)
            stop_loss = round(ltp - atr, 2)
        else:
            target = round(ltp - 1.5 * atr, 2)
            stop_loss = round(ltp + atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "GAMMA_SCALPING",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Gamma Scalp: {', '.join(reasons[:3])}{gamma_info}",
        }
    except Exception as e:
        logger.error(f"Gamma Scalping error for {symbol}: {e}")
        return None


def analyze_iv_crush_play(symbol: str) -> Optional[dict]:
    """
    IV Crush Play: Position for post-event IV collapse.

    Before events (earnings, etc.), IV rises. After the event, IV collapses.
    This strategy identifies high-IV situations and recommends selling
    options or debit spreads to benefit from the crush.

    Entry criteria:
    - Current IV significantly above historical IV (IV Rank > 70)
    - IV skew analysis
    - Use spreads to define risk while benefiting from IV drop

    Best for: Post-event trades or when IV is at extremes
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

        option_chain = get_option_chain(symbol)
        if not option_chain:
            return None

        atm = _get_atm_strike(ltp, option_chain)
        if not atm:
            return None

        current_iv = _estimate_option_iv(atm, "call") * 100

        # Calculate historical volatility
        closes = data["Close"].values
        returns = np.diff(np.log(closes))
        hist_vol = float(np.std(returns) * np.sqrt(252) * 100)

        # IV vs HV ratio
        iv_hv_ratio = current_iv / hist_vol if hist_vol > 0 else 1

        score = 0
        reasons = []

        if iv_hv_ratio > 1.3:
            score += 2
            reasons.append(f"IV={current_iv:.0f}% >> HV={hist_vol:.0f}% (IV/HV={iv_hv_ratio:.2f})")
        elif iv_hv_ratio > 1.15:
            score += 1
            reasons.append(f"IV={current_iv:.0f}% > HV={hist_vol:.0f}%")

        # IV skew analysis
        iv_skew = analyze_iv_skew(option_chain, ltp)
        if iv_skew.get("skew_type") in ["STEEP_PUT_SKEW", "REVERSE_SKEW"]:
            score += 1
            reasons.append(f"IV skew: {iv_skew['skew_type']}")

        # Check if IV is at high percentile
        iv_values = []
        for entry in option_chain:
            call_iv = entry.get("call_iv")
            put_iv = entry.get("put_iv")
            if call_iv:
                iv_values.append(call_iv)
            if put_iv:
                iv_values.append(put_iv)

        if iv_values:
            avg_chain_iv = np.mean(iv_values)
            if avg_chain_iv > 30:
                score += 1
                reasons.append(f"Average chain IV={avg_chain_iv:.0f}% elevated")

        if score < 2:
            return None

        # Recommend iron condor or credit spread for IV crush
        T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
        greeks = calculate_all_greeks(
            ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, current_iv / 100, "call"
        )

        otm_call = _get_strike_by_offset(ltp, option_chain, 0.03)
        otm_put = _get_strike_by_offset(ltp, option_chain, -0.03)

        crush_info = ""
        if otm_call and otm_put:
            call_premium = otm_call["call_ltp"]
            put_premium = otm_put["put_ltp"]
            total_credit = round(call_premium + put_premium, 2)
            crush_info = (
                f" | Sell {otm_call['strike_price']}CE @{call_premium} + "
                f"Sell {otm_put['strike_price']}PE @{put_premium} = {total_credit} credit, "
                f"Vega={greeks['vega']} (profits from IV drop)"
            )

        confidence = min(0.45 + score * 0.1, 0.85)

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "IV_CRUSH_PLAY",
            "entry_price": ltp,
            "target": ltp,
            "stop_loss": round(ltp - 2 * atr, 2),
            "risk_reward": 2.0,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"IV Crush Play: {', '.join(reasons[:3])}{crush_info}",
        }
    except Exception as e:
        logger.error(f"IV Crush error for {symbol}: {e}")
        return None


def analyze_iv_expansion_play(symbol: str) -> Optional[dict]:
    """
    IV Expansion Play: Buy options when IV is cheap, expecting it to rise.

    When IV is at low percentile, options are cheap. Before events or
    when market is complacent, buy options to benefit from IV expansion.

    Entry criteria:
    - IV Rank < 25 (options are cheap)
    - Upcoming catalyst expected
    - Bollinger squeeze or low ADX (calm before storm)
    - Buy straddles/strangles or long options with high vega

    Best for: Pre-event positioning, volatility mean reversion
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
        adx = indicators.get("adx", 25)
        bb_upper = indicators.get("bollinger_upper", ltp * 1.04)
        bb_lower = indicators.get("bollinger_lower", ltp * 0.96)

        option_chain = get_option_chain(symbol)
        if not option_chain:
            return None

        atm = _get_atm_strike(ltp, option_chain)
        if not atm:
            return None

        current_iv = _estimate_option_iv(atm, "call") * 100

        # Calculate HV
        closes = data["Close"].values
        returns = np.diff(np.log(closes))
        hist_vol = float(np.std(returns) * np.sqrt(252) * 100)

        iv_hv_ratio = current_iv / hist_vol if hist_vol > 0 else 1

        score = 0
        reasons = []

        # IV is cheap relative to HV
        if iv_hv_ratio < 0.85:
            score += 2
            reasons.append(f"IV={current_iv:.0f}% << HV={hist_vol:.0f}% (cheap options)")
        elif iv_hv_ratio < 0.95:
            score += 1
            reasons.append(f"IV={current_iv:.0f}% < HV={hist_vol:.0f}%")

        # Bollinger squeeze
        bb_width = (bb_upper - bb_lower) / ltp * 100
        if bb_width < 5:
            score += 2
            reasons.append(f"Bollinger squeeze ({bb_width:.1f}%)")
        elif bb_width < 8:
            score += 1
            reasons.append(f"Narrow Bollinger ({bb_width:.1f}%)")

        if adx < 18:
            score += 1
            reasons.append(f"ADX={adx} very low - breakout setup")

        if score < 3:
            return None

        T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)
        greeks = calculate_all_greeks(
            ltp, atm["strike_price"], T, DEFAULT_RISK_FREE_RATE, current_iv / 100, "call"
        )

        expansion_info = (
            f" | Buy {atm['strike_price']}CE @{atm['call_ltp']} + "
            f"Buy {atm['strike_price']}PE @{atm['put_ltp']}, "
            f"Total Vega={2*greeks['vega']:.4f} (profits from IV rise), "
            f"Gamma={2*greeks['gamma']:.6f}"
        )

        confidence = min(0.4 + score * 0.09, 0.85)
        target = round(ltp + 3 * atr, 2)
        stop_loss = round(ltp - 3 * atr, 2)

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": "BUY",
            "strategy": "IV_EXPANSION_PLAY",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": 2.5,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"IV Expansion: {', '.join(reasons[:3])}{expansion_info}",
        }
    except Exception as e:
        logger.error(f"IV Expansion error for {symbol}: {e}")
        return None


def analyze_oi_breakout(symbol: str) -> Optional[dict]:
    """
    OI-Based Breakout Strategy: Use options chain OI to predict breakout direction.

    High Call OI at a strike = resistance (writers don't expect price above)
    High Put OI at a strike = support (writers don't expect price below)
    When price breaks through high OI level, it often leads to sharp moves
    due to forced hedging (gamma squeeze).

    Entry criteria:
    - Price near max OI level (resistance or support)
    - Technical breakout signal (momentum, volume)
    - OI buildup analysis for support/resistance
    - PCR for sentiment confirmation

    Best for: Breakout trading with options chain confirmation
    """
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

        option_chain = get_option_chain(symbol)
        if not option_chain:
            return None

        oi_data = analyze_oi_buildup(option_chain, ltp)
        pcr_data = calculate_pcr(option_chain)
        max_pain = calculate_max_pain(option_chain)

        score = 0
        reasons = []
        signal = None

        resistance = oi_data.get("resistance_from_oi", 0)
        support = oi_data.get("support_from_oi", 0)

        # Bullish breakout: price near or breaking above call OI resistance
        if resistance > 0 and ltp >= resistance * 0.98:
            score += 2
            signal = "BUY"
            reasons.append(f"Breaking above call OI resistance at {resistance}")

            if pcr_data.get("pcr_oi", 0) > 1.0:
                score += 1
                reasons.append(f"PCR={pcr_data['pcr_oi']} (put heavy, bullish)")

        # Bearish breakdown: price near or breaking below put OI support
        elif support > 0 and ltp <= support * 1.02:
            score += 2
            signal = "SELL"
            reasons.append(f"Breaking below put OI support at {support}")

            if pcr_data.get("pcr_oi", 0) < 0.7:
                score += 1
                reasons.append(f"PCR={pcr_data['pcr_oi']} (call heavy, bearish)")

        if not signal or score < 2:
            return None

        # Max pain analysis
        if signal == "BUY" and max_pain > ltp:
            score += 1
            reasons.append(f"Max Pain at {max_pain} (above spot, bullish pull)")
        elif signal == "SELL" and max_pain < ltp:
            score += 1
            reasons.append(f"Max Pain at {max_pain} (below spot, bearish pull)")

        # Technical confirmation
        if signal == "BUY" and indicators.get("macd_histogram", 0) > 0:
            score += 1
        elif signal == "SELL" and indicators.get("macd_histogram", 0) < 0:
            score += 1

        confidence = min(0.45 + score * 0.08, 0.88)

        oi_info = (
            f" | Max Call OI at {oi_data.get('max_call_oi_strike', 'N/A')} "
            f"({oi_data.get('max_call_oi', 0):,}), "
            f"Max Put OI at {oi_data.get('max_put_oi_strike', 'N/A')} "
            f"({oi_data.get('max_put_oi', 0):,}), "
            f"Max Pain={max_pain}, PCR={pcr_data.get('pcr_oi', 0)}"
        )

        if signal == "BUY":
            target = round(ltp + 3 * atr, 2)
            stop_loss = round(support - atr * 0.5, 2) if support > 0 else round(ltp - 2 * atr, 2)
        else:
            target = round(ltp - 3 * atr, 2)
            stop_loss = round(resistance + atr * 0.5, 2) if resistance > 0 else round(ltp + 2 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "OI_BREAKOUT",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"OI Breakout: {', '.join(reasons[:3])}{oi_info}",
        }
    except Exception as e:
        logger.error(f"OI Breakout error for {symbol}: {e}")
        return None


def analyze_pcr_reversal(symbol: str) -> Optional[dict]:
    """
    PCR Reversal Strategy: Use extreme Put-Call Ratio for contrarian signals.

    Extreme PCR values often indicate market extremes:
    - PCR > 1.5: Extreme bearish sentiment -> contrarian BUY
    - PCR < 0.5: Extreme bullish sentiment -> contrarian SELL
    - Based on crowd psychology: when everyone is bearish, market often reverses

    Entry criteria:
    - Extreme PCR values (>1.3 or <0.5)
    - RSI confirmation (oversold/overbought)
    - Price at support/resistance levels
    - Volume analysis for exhaustion

    Best for: Reversal trading, contrarian plays
    """
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
        rsi = indicators.get("rsi", 50)

        option_chain = get_option_chain(symbol)
        if not option_chain:
            return None

        pcr_data = calculate_pcr(option_chain)
        pcr_oi = pcr_data.get("pcr_oi", 1.0)

        score = 0
        reasons = []
        signal = None

        # Extreme bearish sentiment -> contrarian BUY
        if pcr_oi > 1.5:
            score += 2
            signal = "BUY"
            reasons.append(f"Extreme PCR={pcr_oi} (very bearish crowd = contrarian BUY)")
            if rsi < 35:
                score += 1
                reasons.append(f"RSI={rsi} oversold confirms reversal")
        elif pcr_oi > 1.2:
            score += 1
            signal = "BUY"
            reasons.append(f"High PCR={pcr_oi} (bearish crowd)")
            if rsi < 40:
                score += 1
                reasons.append(f"RSI={rsi} approaching oversold")

        # Extreme bullish sentiment -> contrarian SELL
        elif pcr_oi < 0.4:
            score += 2
            signal = "SELL"
            reasons.append(f"Extreme PCR={pcr_oi} (very bullish crowd = contrarian SELL)")
            if rsi > 65:
                score += 1
                reasons.append(f"RSI={rsi} overbought confirms reversal")
        elif pcr_oi < 0.6:
            score += 1
            signal = "SELL"
            reasons.append(f"Low PCR={pcr_oi} (bullish crowd)")
            if rsi > 60:
                score += 1
                reasons.append(f"RSI={rsi} elevated")

        if not signal or score < 2:
            return None

        # OI distribution confirmation
        oi_data = analyze_oi_buildup(option_chain, ltp)
        max_pain = calculate_max_pain(option_chain)

        pcr_info = (
            f" | Sentiment={pcr_data.get('sentiment', 'N/A')}, "
            f"Call OI={pcr_data.get('total_call_oi', 0):,}, "
            f"Put OI={pcr_data.get('total_put_oi', 0):,}, "
            f"Max Pain={max_pain}"
        )

        confidence = min(0.45 + score * 0.09, 0.85)

        if signal == "BUY":
            target = round(ltp + 3 * atr, 2)
            stop_loss = round(ltp - 2 * atr, 2)
        else:
            target = round(ltp - 3 * atr, 2)
            stop_loss = round(ltp + 2 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "PCR_REVERSAL",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"PCR Reversal: {', '.join(reasons[:3])}{pcr_info}",
        }
    except Exception as e:
        logger.error(f"PCR Reversal error for {symbol}: {e}")
        return None


def analyze_max_pain_magnet(symbol: str) -> Optional[dict]:
    """
    Max Pain Magnet Strategy: Trade toward max pain level near expiry.

    Max Pain theory: option prices tend to gravitate toward the strike
    where option writers (market makers) suffer the least loss.
    Near expiry, this gravitational pull becomes strongest.

    Entry criteria:
    - Price is significantly away from max pain
    - Near expiry (2-5 days)
    - Max pain level is clear and well-defined
    - OI distribution supports convergence

    Best for: Near-expiry trades, mean reversion to max pain
    """
    try:
        data = get_historical_data(symbol, period="1mo", interval="1d")
        if data is None or len(data) < 10:
            return None

        indicators = calculate_indicators(data)
        quote = get_stock_quote(symbol)
        if not quote:
            return None

        ltp = quote["ltp"]
        atr = indicators.get("atr", ltp * 0.02)

        option_chain = get_option_chain(symbol)
        if not option_chain:
            return None

        max_pain = calculate_max_pain(option_chain)
        if max_pain <= 0:
            return None

        # Distance from max pain
        distance_pct = abs(ltp - max_pain) / ltp * 100

        score = 0
        reasons = []
        signal = None

        if distance_pct < 1:
            return None  # Already at max pain, no trade

        if distance_pct >= 2:
            score += 1
            reasons.append(f"Price {distance_pct:.1f}% from Max Pain ({max_pain})")
        if distance_pct >= 4:
            score += 1
            reasons.append(f"Significant gap to Max Pain")

        if ltp > max_pain:
            signal = "SELL"
            reasons.append(f"Price above Max Pain, expect pullback toward {max_pain}")
        else:
            signal = "BUY"
            reasons.append(f"Price below Max Pain, expect rally toward {max_pain}")

        # OI confirmation
        pcr_data = calculate_pcr(option_chain)
        if signal == "BUY" and pcr_data.get("pcr_oi", 0) > 1.0:
            score += 1
            reasons.append(f"PCR={pcr_data['pcr_oi']} supports upside")
        elif signal == "SELL" and pcr_data.get("pcr_oi", 0) < 0.8:
            score += 1
            reasons.append(f"PCR={pcr_data['pcr_oi']} supports downside")

        if score < 2:
            return None

        confidence = min(0.45 + score * 0.09, 0.82)

        target = max_pain
        if signal == "BUY":
            stop_loss = round(ltp - 2 * atr, 2)
        else:
            stop_loss = round(ltp + 2 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        max_pain_info = (
            f" | Max Pain={max_pain}, Distance={distance_pct:.1f}%, "
            f"PCR={pcr_data.get('pcr_oi', 0)}, "
            f"Sentiment={pcr_data.get('sentiment', 'N/A')}"
        )

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "MAX_PAIN_MAGNET",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"Max Pain Magnet: {', '.join(reasons[:3])}{max_pain_info}",
        }
    except Exception as e:
        logger.error(f"Max Pain error for {symbol}: {e}")
        return None


def analyze_gex_strategy(symbol: str) -> Optional[dict]:
    """
    Gamma Exposure (GEX) Strategy: Trade based on market maker hedging flows.

    Positive GEX: Market makers are long gamma - they buy dips and sell rallies
    (suppresses volatility, mean-reverting market).
    Negative GEX: Market makers are short gamma - they sell dips and buy rallies
    (amplifies volatility, trending market).

    Entry criteria:
    - Estimate GEX from option chain data
    - High positive GEX = mean reversion (sell strangles)
    - High negative GEX = momentum (buy options for trend)
    - Zero GEX level as support/resistance

    Best for: Understanding market regime and adjusting strategy accordingly
    """
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

        option_chain = get_option_chain(symbol)
        if not option_chain:
            return None

        # Estimate GEX from option chain
        total_gex = 0
        T = _days_to_years(DEFAULT_MONTHLY_EXPIRY_DAYS)

        for entry in option_chain:
            strike = entry["strike_price"]
            call_oi = entry.get("call_oi", 0)
            put_oi = entry.get("put_oi", 0)
            iv = _estimate_option_iv(entry, "call")

            call_gamma = calculate_all_greeks(
                ltp, strike, T, DEFAULT_RISK_FREE_RATE, iv, "call"
            )["gamma"]
            put_gamma = calculate_all_greeks(
                ltp, strike, T, DEFAULT_RISK_FREE_RATE, iv, "put"
            )["gamma"]

            # GEX = Call OI * Call Gamma - Put OI * Put Gamma
            # (Market makers are typically short calls and long puts from retail)
            gex_at_strike = (call_oi * call_gamma * 100 - put_oi * put_gamma * 100) * ltp
            total_gex += gex_at_strike

        score = 0
        reasons = []
        signal = None

        if total_gex > 0:
            # Positive GEX - mean reverting environment
            reasons.append(f"Positive GEX ({total_gex:,.0f}) - mean reverting market")

            rsi = indicators.get("rsi", 50)
            if rsi > 65:
                signal = "SELL"
                score += 2
                reasons.append(f"RSI={rsi} overbought in positive GEX (sell the rip)")
            elif rsi < 35:
                signal = "BUY"
                score += 2
                reasons.append(f"RSI={rsi} oversold in positive GEX (buy the dip)")
        else:
            # Negative GEX - trending/volatile environment
            reasons.append(f"Negative GEX ({total_gex:,.0f}) - volatile/trending market")

            if indicators.get("macd_histogram", 0) > 0:
                signal = "BUY"
                score += 2
                reasons.append("MACD positive in negative GEX (momentum BUY)")
            elif indicators.get("macd_histogram", 0) < 0:
                signal = "SELL"
                score += 2
                reasons.append("MACD negative in negative GEX (momentum SELL)")

        if not signal or score < 2:
            return None

        pcr_data = calculate_pcr(option_chain)
        gex_info = (
            f" | GEX={total_gex:,.0f}, "
            f"Regime={'Mean-Reverting' if total_gex > 0 else 'Trending'}, "
            f"PCR={pcr_data.get('pcr_oi', 0)}"
        )

        confidence = min(0.45 + score * 0.1, 0.82)

        if signal == "BUY":
            target = round(ltp + 2.5 * atr, 2)
            stop_loss = round(ltp - 1.5 * atr, 2)
        else:
            target = round(ltp - 2.5 * atr, 2)
            stop_loss = round(ltp + 1.5 * atr, 2)

        risk = abs(ltp - stop_loss)
        reward = abs(target - ltp)
        rr = round(reward / risk, 2) if risk > 0 else 0

        return {
            "symbol": symbol,
            "name": quote.get("name", symbol),
            "ltp": ltp,
            "signal": signal,
            "strategy": "GEX_STRATEGY",
            "entry_price": ltp,
            "target": target,
            "stop_loss": stop_loss,
            "risk_reward": rr,
            "confidence": confidence,
            "segment": "OPTIONS",
            "reason": f"GEX Strategy: {', '.join(reasons[:3])}{gex_info}",
        }
    except Exception as e:
        logger.error(f"GEX Strategy error for {symbol}: {e}")
        return None
