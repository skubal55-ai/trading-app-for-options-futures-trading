from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from packages.broker_adapters.stubs import BROKER_REGISTRY

app = FastAPI(title="Execution Service", version="0.1.0")


class ExecuteOrderRequest(BaseModel):
    broker: str = Field(description="e.g. zerodha, upstox")
    order: dict


@app.get("/health")
async def health() -> dict:
    return {"service": "execution_service", "status": "ok"}


@app.post("/orders/execute")
async def execute_order(payload: ExecuteOrderRequest) -> dict:
    key = payload.broker.lower()
    if key not in BROKER_REGISTRY:
        raise HTTPException(status_code=400, detail="Unsupported broker")

    adapter = BROKER_REGISTRY[key]()
    result = await adapter.place_order(payload.order)
    return {"status": "submitted", "broker_response": result}
