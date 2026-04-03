from abc import ABC, abstractmethod
from typing import Dict, List


class BrokerAdapter(ABC):
    name: str

    @abstractmethod
    async def authenticate(self, credentials: Dict) -> Dict:
        raise NotImplementedError

    @abstractmethod
    async def get_balance(self) -> Dict:
        raise NotImplementedError

    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        raise NotImplementedError

    @abstractmethod
    async def place_order(self, order: Dict) -> Dict:
        raise NotImplementedError

    @abstractmethod
    async def modify_order(self, broker_order_id: str, patch: Dict) -> Dict:
        raise NotImplementedError

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> Dict:
        raise NotImplementedError
