from fastapi import FastAPI

from packages.data_adapters import (
    FallbackMarketDataRouter,
    FreeNewsStubProvider,
    NseOptionsStubProvider,
    YahooQuoteStubProvider,
)

app = FastAPI(title="Market Data Service", version="0.1.0")
router = FallbackMarketDataRouter(
    options_providers=[NseOptionsStubProvider()],
    quote_providers=[YahooQuoteStubProvider()],
    news_providers=[FreeNewsStubProvider()],
)


@app.get("/health")
async def health() -> dict:
    return {"service": "market_data_service", "status": "ok"}


@app.get("/options-chain/sample")
async def sample_options_chain(symbol: str = "NIFTY") -> dict:
    return await router.get_options_chain(symbol)


@app.get("/quote/sample")
async def sample_quote(symbol: str = "NIFTY") -> dict:
    return await router.get_quote(symbol)


@app.get("/news/sample")
async def sample_news(symbol: str = "NIFTY") -> dict:
    items = await router.get_news(symbol)
    return {"symbol": symbol, "items": items}
