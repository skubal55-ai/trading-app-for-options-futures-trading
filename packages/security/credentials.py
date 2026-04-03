import base64
import json
import os
from typing import Dict

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.getenv("BROKER_CREDENTIALS_FERNET_KEY", "").strip()
    if not key:
        raise RuntimeError("BROKER_CREDENTIALS_FERNET_KEY is not configured")
    return Fernet(key.encode("utf-8"))


def encrypt_secret_payload(payload: Dict) -> str:
    fernet = _get_fernet()
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    token = fernet.encrypt(raw)
    return base64.urlsafe_b64encode(token).decode("utf-8")


def decrypt_secret_payload(token_str: str) -> Dict:
    fernet = _get_fernet()
    token = base64.urlsafe_b64decode(token_str.encode("utf-8"))
    raw = fernet.decrypt(token)
    return json.loads(raw.decode("utf-8"))
