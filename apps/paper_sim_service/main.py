from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Paper Simulation Service", version="0.1.0")


class PaperRunResult(BaseModel):
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
