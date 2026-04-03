from fastapi import FastAPI

from packages.domain_models import PreTradeCheckRequest
from packages.shared_utils import pre_trade_risk_check

app = FastAPI(title="Risk Service", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"service": "risk_service", "status": "ok"}


@app.post("/pretrade-check")
async def pretrade_check(payload: PreTradeCheckRequest) -> dict:
    ok, reason = pre_trade_risk_check(payload.model_dump())
    return {"allowed": ok, "reason": reason}
