from typing import Dict, Tuple


def pre_trade_risk_check(payload: Dict) -> Tuple[bool, str]:
    deployed = max(float(payload["deployed_capital"]), 1.0)
    total_open_risk = float(payload.get("total_open_risk_amount", 0))
    per_unit_risk = abs(float(payload["entry"]) - float(payload["stop"]))
    new_trade_risk = per_unit_risk * int(payload["quantity"])

    if (total_open_risk + new_trade_risk) > (0.05 * deployed):
        return False, "Risk cap breach: exceeds 5% of deployed capital"

    if float(payload.get("daily_realized_loss", 0)) <= -float(payload["max_daily_loss_amount"]):
        return False, "Daily loss limit reached"

    if int(payload.get("open_positions_count", 0)) >= int(payload["max_open_positions"]):
        return False, "Max open positions exceeded"

    if int(payload.get("slippage_estimate_bps", 0)) > int(payload["max_slippage_bps"]):
        return False, "Slippage threshold exceeded"

    if bool(payload.get("is_stale_quote", False)):
        return False, "Stale quote rejected"

    return True, "OK"


def can_enable_live(metrics: Dict, cfg: Dict) -> bool:
    return all(
        [
            int(metrics["trades"]) >= int(cfg["PAPER_MIN_TRADES"]),
            float(metrics["profit_factor"]) >= float(cfg["PAPER_MIN_PROFIT_FACTOR"]),
            float(metrics["max_drawdown_pct"]) <= float(cfg["PAPER_MAX_DRAWDOWN_PCT"]),
            float(metrics["expectancy"]) >= float(cfg["PAPER_MIN_EXPECTANCY"]),
        ]
    )
