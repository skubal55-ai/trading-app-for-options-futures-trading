from abc import ABC, abstractmethod
from typing import Dict, List


class OptionsChainProvider(ABC):
    name: str

    @abstractmethod
    async def get_options_chain(self, symbol: str) -> Dict:
        raise NotImplementedError


class QuotesProvider(ABC):
    name: str

    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict:
        raise NotImplementedError


class NewsProvider(ABC):
    name: str

    @abstractmethod
    async def get_news(self, symbol: str) -> List[Dict]:
        raise NotImplementedError
