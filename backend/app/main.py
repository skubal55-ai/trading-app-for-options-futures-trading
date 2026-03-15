from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import market, analysis, screener, trading, kite, options_analysis, backtest


app = FastAPI(
    title="NSE Trading Tool API",
    description="Live NSE market data, technical analysis, screeners, and paper/live trading",
    version="1.0.0",
)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(market.router)
app.include_router(analysis.router)
app.include_router(screener.router)
app.include_router(trading.router)
app.include_router(options_analysis.router)
app.include_router(backtest.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
