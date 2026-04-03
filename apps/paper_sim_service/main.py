import os

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from packages.db import get_db
from packages.db.models import LiveModeState, PaperRunMetric
from packages.shared_utils import can_enable_live

app = FastAPI(title="Paper Simulation Service", version="0.1.0")


class PaperRunResult(BaseModel):
    strategy_id: str = "composite_portfolio"
    trades: int
    profit_factor: float
    max_drawdown_pct: float
    expectancy: float
    gate_status: str


@app.get("/health")
async def health() -> dict:
    return {"service": "paper_sim_service", "status": "ok"}


@app.get("/paper-run/sample", response_model=PaperRunResult)
async def paper_run_sample() -> PaperRunResult:
    return PaperRunResult(
        trades=42,
        profit_factor=1.24,
        max_drawdown_pct=9.3,
        expectancy=0.08,
        gate_status="pass",
    )


@app.post("/paper-run/record", response_model=PaperRunResult)
async def record_paper_run(payload: PaperRunResult, db: Session = Depends(get_db)) -> PaperRunResult:
    cfg = {
        "PAPER_MIN_TRADES": os.getenv("PAPER_MIN_TRADES", "30"),
        "PAPER_MIN_PROFIT_FACTOR": os.getenv("PAPER_MIN_PROFIT_FACTOR", "1.1"),
        "PAPER_MAX_DRAWDOWN_PCT": os.getenv("PAPER_MAX_DRAWDOWN_PCT", "12"),
        "PAPER_MIN_EXPECTANCY": os.getenv("PAPER_MIN_EXPECTANCY", "0.01"),
    }
    metrics = payload.model_dump()
    enabled = can_enable_live(metrics, cfg)
    gate_status = "pass" if enabled else "fail"

    row = PaperRunMetric(
        strategy_id=payload.strategy_id,
        trades=payload.trades,
        profit_factor=payload.profit_factor,
        max_drawdown_pct=payload.max_drawdown_pct,
        expectancy=payload.expectancy,
        gate_status=gate_status,
    )
    db.add(row)

    state = db.query(LiveModeState).filter(LiveModeState.id == 1).one_or_none()
    reason = "Paper gate thresholds passed" if enabled else "Paper gate thresholds not met"
    if state is None:
        state = LiveModeState(id=1, enabled=enabled, reason=reason)
        db.add(state)
    else:
        state.enabled = enabled
        state.reason = reason

    db.commit()
    return PaperRunResult(**{**metrics, "gate_status": gate_status})
