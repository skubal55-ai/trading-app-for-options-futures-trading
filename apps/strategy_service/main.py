from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.db import get_db
from packages.db.models import Signal
from packages.domain_models import TipPayload
from packages.strategy_plugins import build_tip_from_context, run_backtest_stub

app = FastAPI(title="Strategy Service", version="0.1.0")


class EvaluateRequest(BaseModel):
    symbol: str = "NIFTY"
    strategy_id: str = Field(default="trend_ema_pullback")
    position_size: int = 10


class BacktestRequest(BaseModel):
    strategy_id: str = Field(default="trend_ema_pullback")
    candles: list[dict]


@app.get("/health")
async def health() -> dict:
    return {"service": "strategy_service", "status": "ok"}


@app.get("/signal/sample", response_model=TipPayload)
async def signal_sample() -> TipPayload:
    context = {
        "symbol": "RELIANCE",
        "quote": {"last_price": 2985.0},
        "position_size": 20,
    }
    tip = build_tip_from_context(context, "trend_ema_pullback")
    return TipPayload(**tip)


@app.post("/signal/evaluate", response_model=TipPayload)
async def evaluate(req: EvaluateRequest, db: Session = Depends(get_db)) -> TipPayload:
    context = {
        "symbol": req.symbol,
        "quote": {"last_price": 24050.35},
        "position_size": req.position_size,
    }
    try:
        tip = build_tip_from_context(context, req.strategy_id)
        signal = Signal(
            instrument=tip["instrument"],
            segment=tip["segment"],
            action=tip["action"],
            entry=tip["entry"],
            stop=tip["stop"],
            target=tip["target"],
            confidence=tip["confidence"],
            strategy_id=tip["strategy_id"],
            explanation=tip["explanation"],
        )
        db.add(signal)
        db.commit()
        return TipPayload(**tip)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/backtest/run")
async def run_backtest(req: BacktestRequest) -> dict:
    return run_backtest_stub(req.candles, req.strategy_id)
