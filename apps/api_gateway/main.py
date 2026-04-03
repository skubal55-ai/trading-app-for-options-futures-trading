import os
from fastapi import Depends, FastAPI
import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.db import Base, engine
from packages.db import models as _db_models  # noqa: F401
from packages.db import get_db
from packages.db.models import LiveModeState
from packages.domain_models import PaperMetrics, PreTradeCheckRequest, TipPayload
from packages.shared_utils import can_enable_live, pre_trade_risk_check

app = FastAPI(title="API Gateway", version="0.1.0")


class AlertChannel(BaseModel):
    channel: str = Field(description="telegram or whatsapp")
    to: str | None = None


class PaperMetricsInput(BaseModel):
    strategy_id: str = "composite_portfolio"
    trades: int = 30
    profit_factor: float = 1.1
    max_drawdown_pct: float = 12.0
    expectancy: float = 0.01


class TradeCycleRequest(BaseModel):
    mode: str = Field(default="paper", description="paper or live")
    symbol: str = "NIFTY"
    strategy_id: str = "trend_ema_pullback"
    position_size: int = 10
    broker: str = "zerodha"
    deployed_capital: float = 100000
    total_open_risk_amount: float = 0
    daily_realized_loss: float = 0
    max_daily_loss_amount: float = 5000
    open_positions_count: int = 0
    max_open_positions: int = 8
    slippage_estimate_bps: int = 8
    max_slippage_bps: int = 25
    is_stale_quote: bool = False
    alerts: list[AlertChannel] = Field(default_factory=list)
    paper_metrics: PaperMetricsInput | None = None


@app.get("/health")
async def health() -> dict:
    return {"service": "api_gateway", "status": "ok"}


@app.post("/api/v1/system/db/init")
async def init_db() -> dict:
    Base.metadata.create_all(bind=engine)
    return {"db_initialized": True}


@app.get("/api/v1/tips/sample", response_model=TipPayload)
async def sample_tip() -> TipPayload:
    return TipPayload(
        instrument="NIFTY",
        segment="OPTION",
        action="BUY",
        entry=225.0,
        stop=210.0,
        target=255.0,
        risk_reward=2.0,
        position_size=50,
        confidence=0.72,
        strategy_id="breakout_atr_volume",
        explanation="Breakout confirmed by volume expansion and trend filter alignment.",
    )


@app.post("/api/v1/risk/pretrade-check")
async def pretrade_check(payload: PreTradeCheckRequest) -> dict:
    ok, reason = pre_trade_risk_check(payload.model_dump())
    return {"allowed": ok, "reason": reason}


@app.post("/api/v1/live/enable")
async def enable_live(metrics: PaperMetrics, db: Session = Depends(get_db)) -> dict:
    cfg = {
        "PAPER_MIN_TRADES": os.getenv("PAPER_MIN_TRADES", "30"),
        "PAPER_MIN_PROFIT_FACTOR": os.getenv("PAPER_MIN_PROFIT_FACTOR", "1.1"),
        "PAPER_MAX_DRAWDOWN_PCT": os.getenv("PAPER_MAX_DRAWDOWN_PCT", "12"),
        "PAPER_MIN_EXPECTANCY": os.getenv("PAPER_MIN_EXPECTANCY", "0.01"),
    }
    enabled = can_enable_live(metrics.model_dump(), cfg)
    reason = "Manual gate check passed" if enabled else "Manual gate check failed"
    state = db.query(LiveModeState).filter(LiveModeState.id == 1).one_or_none()
    if state is None:
        state = LiveModeState(id=1, enabled=enabled, reason=reason)
        db.add(state)
    else:
        state.enabled = enabled
        state.reason = reason
    db.commit()
    return {"live_mode_enabled": enabled, "criteria": cfg, "reason": reason}


@app.get("/api/v1/live/status")
async def live_status(db: Session = Depends(get_db)) -> dict:
    state = db.query(LiveModeState).filter(LiveModeState.id == 1).one_or_none()
    if state is None:
        return {"enabled": False, "reason": "No state recorded yet"}
    return {"enabled": state.enabled, "reason": state.reason, "updated_at": state.updated_at}


@app.post("/api/v1/strategy/evaluate")
async def evaluate_strategy(payload: dict) -> dict:
    base = os.getenv("STRATEGY_SERVICE_URL", "http://strategy_service:8002")
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{base}/signal/evaluate", json=payload)
    return {"upstream_status": resp.status_code, "data": resp.json()}


@app.post("/api/v1/orchestrate/trade-cycle")
async def trade_cycle(payload: TradeCycleRequest, db: Session = Depends(get_db)) -> dict:
    strategy_base = os.getenv("STRATEGY_SERVICE_URL", "http://strategy_service:8002")
    risk_base = os.getenv("RISK_SERVICE_URL", "http://risk_service:8003")
    execution_base = os.getenv("EXECUTION_SERVICE_URL", "http://execution_service:8004")
    paper_base = os.getenv("PAPER_SIM_SERVICE_URL", "http://paper_sim_service:8005")
    notification_base = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification_service:8006")

    async with httpx.AsyncClient(timeout=10.0) as client:
        strategy_resp = await client.post(
            f"{strategy_base}/signal/evaluate",
            json={
                "symbol": payload.symbol,
                "strategy_id": payload.strategy_id,
                "position_size": payload.position_size,
            },
        )
        strategy_data = strategy_resp.json()
        if strategy_resp.status_code >= 400:
            return {"ok": False, "stage": "strategy", "error": strategy_data}

        risk_req = {
            "deployed_capital": payload.deployed_capital,
            "total_open_risk_amount": payload.total_open_risk_amount,
            "entry": strategy_data["entry"],
            "stop": strategy_data["stop"],
            "quantity": strategy_data["position_size"],
            "daily_realized_loss": payload.daily_realized_loss,
            "max_daily_loss_amount": payload.max_daily_loss_amount,
            "open_positions_count": payload.open_positions_count,
            "max_open_positions": payload.max_open_positions,
            "slippage_estimate_bps": payload.slippage_estimate_bps,
            "max_slippage_bps": payload.max_slippage_bps,
            "is_stale_quote": payload.is_stale_quote,
        }
        risk_resp = await client.post(f"{risk_base}/pretrade-check", json=risk_req)
        risk_data = risk_resp.json()
        if not risk_data.get("allowed", False):
            return {"ok": False, "stage": "risk", "signal": strategy_data, "risk": risk_data}

        live_state = db.query(LiveModeState).filter(LiveModeState.id == 1).one_or_none()
        mode = payload.mode.lower()
        if mode not in {"paper", "live"}:
            return {"ok": False, "stage": "input", "error": "mode must be paper or live"}

        execution_result = None
        paper_result = None
        journal_result = None
        if mode == "live":
            if live_state is None or not live_state.enabled:
                return {"ok": False, "stage": "live_gate", "error": "Live mode is disabled. Complete paper gate first."}

            execution_req = {
                "broker": payload.broker,
                "order": {
                    "instrument": strategy_data["instrument"],
                    "quantity": strategy_data["position_size"],
                    "price": strategy_data["entry"],
                    "side": strategy_data["action"],
                    "segment": strategy_data["segment"],
                },
            }
            exec_resp = await client.post(f"{execution_base}/orders/execute", json=execution_req)
            execution_result = exec_resp.json()
            if exec_resp.status_code >= 400:
                return {"ok": False, "stage": "execution", "signal": strategy_data, "error": execution_result}
        else:
            paper_payload = payload.paper_metrics.model_dump() if payload.paper_metrics else {
                "strategy_id": payload.strategy_id,
                "trades": 30,
                "profit_factor": 1.12,
                "max_drawdown_pct": 11.5,
                "expectancy": 0.03,
                "gate_status": "unknown",
            }
            paper_resp = await client.post(f"{paper_base}/paper-run/record", json=paper_payload)
            paper_result = paper_resp.json()

        journal_note = (
            f"[{mode}] {strategy_data['strategy_id']} on {strategy_data['instrument']} "
            f"{strategy_data['action']} entry={strategy_data['entry']} stop={strategy_data['stop']} "
            f"target={strategy_data['target']} confidence={strategy_data['confidence']}"
        )
        jr_resp = await client.post(
            f"{execution_base}/journal/append",
            json={"strategy_id": strategy_data["strategy_id"], "note": journal_note, "pnl": 0.0},
        )
        journal_result = jr_resp.json()

        notification_results = []
        channels = payload.alerts or [AlertChannel(channel="telegram"), AlertChannel(channel="whatsapp")]
        for alert in channels:
            msg = (
                f"{mode.upper()} SIGNAL: {strategy_data['instrument']} {strategy_data['action']} "
                f"@ {strategy_data['entry']} SL {strategy_data['stop']} TGT {strategy_data['target']} "
                f"Conf {strategy_data['confidence']} Strategy {strategy_data['strategy_id']}"
            )
            ntf_resp = await client.post(
                f"{notification_base}/alerts/send",
                json={"channel": alert.channel, "to": alert.to, "message": msg},
            )
            notification_results.append({"channel": alert.channel, "response": ntf_resp.json()})

    return {
        "ok": True,
        "mode": mode,
        "signal": strategy_data,
        "risk": risk_data,
        "execution": execution_result,
        "paper": paper_result,
        "journal": journal_result,
        "notifications": notification_results,
    }
