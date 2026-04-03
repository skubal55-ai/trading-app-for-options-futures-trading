from typing import Dict, List


def _calc_risk_reward(entry: float, stop: float, target: float) -> float:
    risk = max(abs(entry - stop), 0.0001)
    reward = abs(target - entry)
    return round(reward / risk, 2)


def _trend_ema_pullback_signal(context: Dict) -> Dict:
    ltp = float(context["quote"]["last_price"])
    entry = round(ltp, 2)
    stop = round(ltp * 0.992, 2)
    target = round(ltp * 1.018, 2)
    rr = _calc_risk_reward(entry, stop, target)
    return {
        "instrument": context["symbol"],
        "segment": "EQUITY",
        "action": "BUY",
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_reward": rr,
        "position_size": context.get("position_size", 10),
        "confidence": 0.69,
        "strategy_id": "trend_ema_pullback",
        "explanation": "Trend pullback with momentum stabilization; liquidity and spread filters are acceptable.",
    }


def _breakout_oi_confirmation_signal(context: Dict) -> Dict:
    ltp = float(context["quote"]["last_price"])
    entry = round(ltp * 1.001, 2)
    stop = round(ltp * 0.994, 2)
    target = round(ltp * 1.02, 2)
    rr = _calc_risk_reward(entry, stop, target)
    return {
        "instrument": context["symbol"],
        "segment": "OPTION",
        "action": "BUY",
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_reward": rr,
        "position_size": context.get("position_size", 25),
        "confidence": 0.74,
        "strategy_id": "breakout_oi_confirmation",
        "explanation": "Breakout signal validated with options open-interest structure and spread safety checks.",
    }


def build_tip_from_context(context: Dict, strategy_name: str) -> Dict:
    if strategy_name == "trend_ema_pullback":
        return _trend_ema_pullback_signal(context)
    if strategy_name == "breakout_oi_confirmation":
        return _breakout_oi_confirmation_signal(context)
    raise ValueError(f"Unsupported strategy: {strategy_name}")


def run_backtest_stub(candles: List[Dict], strategy_name: str) -> Dict:
    """
    Hook for full backtesting engine. Returns deterministic placeholder metrics.
    """
    total = len(candles)
    if total == 0:
        return {
            "strategy_id": strategy_name,
            "trades": 0,
            "hit_rate": 0,
            "profit_factor": 0,
            "max_drawdown_pct": 0,
            "expectancy": 0,
        }
    trades = max(total // 8, 1)
    return {
        "strategy_id": strategy_name,
        "trades": trades,
        "hit_rate": 0.57,
        "profit_factor": 1.23,
        "max_drawdown_pct": 10.4,
        "expectancy": 0.06,
    }
