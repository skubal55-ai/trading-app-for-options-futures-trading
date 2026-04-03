from datetime import datetime, timezone
from typing import Dict, List

from .base import NewsProvider, OptionsChainProvider, QuotesProvider


class NseOptionsStubProvider(OptionsChainProvider):
    name = "nse_stub"

    async def get_options_chain(self, symbol: str) -> Dict:
        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": self.name,
            "strikes": [
                {"strike": 24000, "ce_ltp": 118.2, "pe_ltp": 104.5, "oi_ce": 186000, "oi_pe": 221000},
                {"strike": 24100, "ce_ltp": 95.4, "pe_ltp": 123.1, "oi_ce": 210000, "oi_pe": 194000},
            ],
        }


class YahooQuoteStubProvider(QuotesProvider):
    name = "yahoo_stub"

    async def get_quote(self, symbol: str) -> Dict:
        return {"symbol": symbol, "last_price": 24050.35, "timestamp": datetime.now(timezone.utc).isoformat(), "source": self.name}


class FreeNewsStubProvider(NewsProvider):
    name = "free_news_stub"

    async def get_news(self, symbol: str) -> List[Dict]:
        return [
            {
                "symbol": symbol,
                "headline": f"{symbol} sees elevated options activity",
                "sentiment": "neutral_to_positive",
                "source": self.name,
            }
        ]


class FallbackMarketDataRouter:
    """
    Tries providers in order and returns first successful response.
    """

    def __init__(
        self,
        options_providers: List[OptionsChainProvider],
        quote_providers: List[QuotesProvider],
        news_providers: List[NewsProvider],
    ) -> None:
        self.options_providers = options_providers
        self.quote_providers = quote_providers
        self.news_providers = news_providers

    async def get_options_chain(self, symbol: str) -> Dict:
        last_error = None
        for provider in self.options_providers:
            try:
                return await provider.get_options_chain(symbol)
            except Exception as exc:  # pragma: no cover - fallback safety
                last_error = str(exc)
        raise RuntimeError(f"All options providers failed: {last_error}")

    async def get_quote(self, symbol: str) -> Dict:
        last_error = None
        for provider in self.quote_providers:
            try:
                return await provider.get_quote(symbol)
            except Exception as exc:  # pragma: no cover - fallback safety
                last_error = str(exc)
        raise RuntimeError(f"All quote providers failed: {last_error}")

    async def get_news(self, symbol: str) -> List[Dict]:
        last_error = None
        for provider in self.news_providers:
            try:
                return await provider.get_news(symbol)
            except Exception as exc:  # pragma: no cover - fallback safety
                last_error = str(exc)
        raise RuntimeError(f"All news providers failed: {last_error}")
