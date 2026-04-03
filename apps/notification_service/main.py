from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Notification Service", version="0.1.0")


class AlertRequest(BaseModel):
    channel: str
    message: str


@app.get("/health")
async def health() -> dict:
    return {"service": "notification_service", "status": "ok"}


@app.post("/alerts/send")
async def send_alert(payload: AlertRequest) -> dict:
    channel = payload.channel.lower()
    if channel not in {"telegram", "whatsapp"}:
        return {"sent": False, "reason": "Unsupported channel"}
    return {"sent": True, "channel": channel, "preview": payload.message[:120]}
