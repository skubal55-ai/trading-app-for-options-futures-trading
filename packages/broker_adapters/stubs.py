from typing import Dict, List

from .base import BrokerAdapter


class _StubBroker(BrokerAdapter):
    name = "stub"

    async def authenticate(self, credentials: Dict) -> Dict:
        return {"broker": self.name, "status": "ok", "note": "stub adapter"}

    async def get_balance(self) -> Dict:
        return {"broker": self.name, "cash": 0, "margin": 0}

    async def get_positions(self) -> List[Dict]:
        return []

    async def place_order(self, order: Dict) -> Dict:
        return {"broker": self.name, "status": "accepted", "order": order}

    async def modify_order(self, broker_order_id: str, patch: Dict) -> Dict:
        return {"broker": self.name, "order_id": broker_order_id, "status": "modified", "patch": patch}

    async def cancel_order(self, broker_order_id: str) -> Dict:
        return {"broker": self.name, "order_id": broker_order_id, "status": "cancelled"}


class ZerodhaAdapter(_StubBroker):
    name = "zerodha"


class UpstoxAdapter(_StubBroker):
    name = "upstox"


class AngelOneAdapter(_StubBroker):
    name = "angel_one"


class FyersAdapter(_StubBroker):
    name = "fyers"


class DhanAdapter(_StubBroker):
    name = "dhan"


class FivePaisaAdapter(_StubBroker):
    name = "5paisa"


class AliceBlueAdapter(_StubBroker):
    name = "alice_blue"


class GrowwAdapter(_StubBroker):
    name = "groww"


BROKER_REGISTRY = {
    "zerodha": ZerodhaAdapter,
    "upstox": UpstoxAdapter,
    "angel_one": AngelOneAdapter,
    "fyers": FyersAdapter,
    "dhan": DhanAdapter,
    "5paisa": FivePaisaAdapter,
    "alice_blue": AliceBlueAdapter,
    "groww": GrowwAdapter,
}
