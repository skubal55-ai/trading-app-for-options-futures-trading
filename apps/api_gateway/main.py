import os
from fastapi import FastAPI
import httpx

from packages.db import Base, engine
from packages.db import models as _db_models  # noqa: F401
from packages.domain_models import PaperMetrics, PreTradeCheckRequest, TipPayload
from packages.shared_utils import can_enable_live, pre_trade_risk_check

app = FastAPI(title="API Gateway", version="0.1.0")


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
async def enable_live(metrics: PaperMetrics) -> dict:
    cfg = {
        "PAPER_MIN_TRADES": os.getenv("PAPER_MIN_TRADES", "30"),
        "PAPER_MIN_PROFIT_FACTOR": os.getenv("PAPER_MIN_PROFIT_FACTOR", "1.1"),
        "PAPER_MAX_DRAWDOWN_PCT": os.getenv("PAPER_MAX_DRAWDOWN_PCT", "12"),
        "PAPER_MIN_EXPECTANCY": os.getenv("PAPER_MIN_EXPECTANCY", "0.01"),
    }
    enabled = can_enable_live(metrics.model_dump(), cfg)
    return {"live_mode_enabled": enabled, "criteria": cfg}


@app.post("/api/v1/strategy/evaluate")
async def evaluate_strategy(payload: dict) -> dict:
    base = os.getenv("STRATEGY_SERVICE_URL", "http://strategy_service:8002")
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{base}/signal/evaluate", json=payload)
    return {"upstream_status": resp.status_code, "data": resp.json()}
