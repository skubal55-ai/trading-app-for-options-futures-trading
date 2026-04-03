from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.broker_adapters.stubs import BROKER_REGISTRY
from packages.db import get_db
from packages.db.models import BrokerCredential, Order, TradeJournal
from packages.security import decrypt_secret_payload, encrypt_secret_payload

app = FastAPI(title="Execution Service", version="0.1.0")


class ExecuteOrderRequest(BaseModel):
    broker: str = Field(description="e.g. zerodha, upstox")
    order: dict


class BrokerCredentialsRequest(BaseModel):
    broker: str
    credentials: dict


class JournalRequest(BaseModel):
    strategy_id: str
    note: str
    pnl: float = 0.0


@app.get("/health")
async def health() -> dict:
    return {"service": "execution_service", "status": "ok"}


@app.post("/brokers/credentials/upsert")
async def upsert_broker_credentials(payload: BrokerCredentialsRequest, db: Session = Depends(get_db)) -> dict:
    broker_key = payload.broker.lower()
    if broker_key not in BROKER_REGISTRY:
        raise HTTPException(status_code=400, detail="Unsupported broker")

    encrypted_payload = encrypt_secret_payload(payload.credentials)
    record = db.query(BrokerCredential).filter(BrokerCredential.broker == broker_key).one_or_none()
    if record is None:
        record = BrokerCredential(broker=broker_key, encrypted_payload=encrypted_payload)
        db.add(record)
    else:
        record.encrypted_payload = encrypted_payload
    db.commit()
    return {"saved": True, "broker": broker_key}


@app.post("/brokers/{broker}/authenticate")
async def authenticate_broker(broker: str, db: Session = Depends(get_db)) -> dict:
    broker_key = broker.lower()
    if broker_key not in BROKER_REGISTRY:
        raise HTTPException(status_code=400, detail="Unsupported broker")
    record = db.query(BrokerCredential).filter(BrokerCredential.broker == broker_key).one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Credentials not found for broker")

    creds = decrypt_secret_payload(record.encrypted_payload)
    adapter = BROKER_REGISTRY[broker_key]()
    result = await adapter.authenticate(creds)
    if result.get("status") != "ok":
        raise HTTPException(status_code=401, detail=f"Authentication failed: {result.get('reason', 'unknown')}")
    return {"authenticated": True, "broker": broker_key, "result": result}


@app.post("/orders/execute")
async def execute_order(payload: ExecuteOrderRequest, db: Session = Depends(get_db)) -> dict:
    key = payload.broker.lower()
    if key not in BROKER_REGISTRY:
        raise HTTPException(status_code=400, detail="Unsupported broker")

    record = db.query(BrokerCredential).filter(BrokerCredential.broker == key).one_or_none()
    if record is None:
        raise HTTPException(status_code=400, detail="Broker credentials missing. Save credentials first.")

    adapter = BROKER_REGISTRY[key]()
    creds = decrypt_secret_payload(record.encrypted_payload)
    auth_result = await adapter.authenticate(creds)
    if auth_result.get("status") != "ok":
        raise HTTPException(status_code=401, detail=f"Authentication failed: {auth_result.get('reason', 'unknown')}")
    result = await adapter.place_order(payload.order)
    persisted = Order(
        broker=key,
        broker_order_id=str(result.get("order_id", result.get("status", "accepted"))),
        instrument=str(payload.order.get("instrument", "UNKNOWN")),
        status=str(result.get("status", "accepted")),
        quantity=int(payload.order.get("quantity", 0)),
        avg_price=float(payload.order.get("price", 0)),
    )
    db.add(persisted)
    db.commit()
    return {"status": "submitted", "broker_response": result, "order_saved": True}


@app.post("/journal/append")
async def append_journal(payload: JournalRequest, db: Session = Depends(get_db)) -> dict:
    row = TradeJournal(strategy_id=payload.strategy_id, note=payload.note, pnl=payload.pnl)
    db.add(row)
    db.commit()
    return {"saved": True, "journal_id": row.id}
