"""Router for Zerodha Kite Connect integration."""
from fastapi import APIRouter, Query
from typing import Optional
from app.services.kite_integration import (
    configure_kite,
    generate_session,
    get_kite_status,
    get_kite_quote,
    get_kite_historical,
    get_kite_option_chain,
    get_kite_positions,
    get_kite_orders,
    disconnect_kite,
)
router = APIRouter(prefix="/api/kite", tags=["Kite Connect"])
@router.post("/configure")
async def configure(api_key: str, api_secret: str):
    """Configure Kite API credentials and get login URL."""
    return configure_kite(api_key, api_secret)
@router.post("/session")
async def create_session(request_token: str):
    """Generate session after OAuth login. Pass the request_token from redirect URL."""
    return generate_session(request_token)
@router.get("/status")
async def kite_status():
    """Check Kite connection status."""
    return get_kite_status()
@router.get("/quote/{symbol}")
async def kite_quote(symbol: str):
    """Get live quote from Kite for a symbol."""
    quote = get_kite_quote(symbol.upper())
    if not quote:
        return {"error": "Not connected to Kite or symbol not found", "symbol": symbol}
    return quote
@router.get("/historical/{symbol}")
async def kite_historical(
    symbol: str,
    interval: str = Query(default="day", description="day, minute, 3minute, 5minute, etc."),
    days: int = Query(default=180, description="Number of days of data"),
):
    """Get historical data from Kite."""
    data = get_kite_historical(symbol.upper(), interval, days)
    if not data:
        return {"error": "Not connected or no data", "symbol": symbol}
    return {"symbol": symbol, "data": data}
@router.get("/option-chain/{symbol}")
async def kite_option_chain(symbol: str):
    """Get option chain from Kite for index/stock."""
    chain = get_kite_option_chain(symbol.upper())
    if not chain:
        return {"error": "Not connected or no options data", "symbol": symbol}
    return {"symbol": symbol, "chain": chain}
@router.get("/positions")
async def kite_positions():
    """Get live positions from Kite."""
    return {"positions": get_kite_positions()}
@router.get("/orders")
async def kite_orders():
    """Get orders from Kite."""
    return {"orders": get_kite_orders()}
@router.post("/disconnect")
async def kite_disconnect():
    """Disconnect from Kite."""
    return disconnect_kite()
