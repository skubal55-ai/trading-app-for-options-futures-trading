import os

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Notification Service", version="0.1.0")


class AlertRequest(BaseModel):
    channel: str
    message: str
    to: str | None = None


@app.get("/health")
async def health() -> dict:
    return {"service": "notification_service", "status": "ok"}


@app.post("/alerts/send")
async def send_alert(payload: AlertRequest) -> dict:
    channel = payload.channel.lower()
    if channel not in {"telegram", "whatsapp"}:
        return {"sent": False, "reason": "Unsupported channel"}
    if channel == "telegram":
        return await _send_telegram(payload)
    return await _send_whatsapp(payload)


async def _send_telegram(payload: AlertRequest) -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = payload.to or os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return {"sent": False, "channel": "telegram", "reason": "Missing TELEGRAM_BOT_TOKEN or chat id"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = {"chat_id": chat_id, "text": payload.message}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=body)
    return {"sent": resp.is_success, "channel": "telegram", "status_code": resp.status_code}


async def _send_whatsapp(payload: AlertRequest) -> dict:
    provider = os.getenv("WHATSAPP_PROVIDER", "twilio").lower()
    if provider == "twilio":
        return await _send_whatsapp_twilio(payload)
    return await _send_whatsapp_generic(payload)


async def _send_whatsapp_twilio(payload: AlertRequest) -> dict:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_WHATSAPP_FROM", "").strip()
    to_number = payload.to or os.getenv("WHATSAPP_TO", "").strip()
    if not account_sid or not auth_token or not from_number or not to_number:
        return {"sent": False, "channel": "whatsapp", "reason": "Missing Twilio WhatsApp credentials"}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    data = {"From": from_number, "To": to_number, "Body": payload.message}
    async with httpx.AsyncClient(timeout=10.0, auth=(account_sid, auth_token)) as client:
        resp = await client.post(url, data=data)
    return {"sent": resp.is_success, "channel": "whatsapp", "provider": "twilio", "status_code": resp.status_code}


async def _send_whatsapp_generic(payload: AlertRequest) -> dict:
    base_url = os.getenv("WHATSAPP_API_BASE_URL", "").strip()
    api_key = os.getenv("WHATSAPP_API_KEY", "").strip()
    to_number = payload.to or os.getenv("WHATSAPP_TO", "").strip()
    if not base_url or not api_key or not to_number:
        return {"sent": False, "channel": "whatsapp", "reason": "Missing generic WhatsApp provider credentials"}

    headers = {"Authorization": f"Bearer {api_key}"}
    body = {"to": to_number, "message": payload.message}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(base_url, json=body, headers=headers)
    return {"sent": resp.is_success, "channel": "whatsapp", "provider": "generic", "status_code": resp.status_code}
