"""
Zerodha Kite Connect Integration for live market data and order execution.
Requires kiteconnect package and valid API credentials.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta
logger = logging.getLogger(__name__)
# Kite connection state
kite_session = {
    "connected": False,
    "api_key": "",
    "api_secret": "",
    "access_token": "",
    "request_token": "",
    "user_id": "",
    "login_url": "",
}
def configure_kite(api_key: str, api_secret: str) -> dict:
    """Configure Kite API credentials and generate login URL."""
    kite_session["api_key"] = api_key
    kite_session["api_secret"] = api_secret
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=api_key)
        login_url = kite.login_url()
        kite_session["login_url"] = login_url
        return {
            "status": "configured",
            "login_url": login_url,
            "message": "Open the login URL in your browser, complete login, and provide the request_token from the redirect URL.",
        }
    except ImportError:
        kite_session["login_url"] = f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"
        return {
            "status": "configured",
            "login_url": kite_session["login_url"],
            "message": "kiteconnect package not installed. Install with: pip install kiteconnect. Login URL generated for manual flow.",
        }
    except Exception as e:
        logger.error(f"Kite configuration error: {e}")
        return {"status": "error", "message": str(e)}
def generate_session(request_token: str) -> dict:
    """Generate Kite session using request token from OAuth redirect."""
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=kite_session["api_key"])
        data = kite.generate_session(request_token, api_secret=kite_session["api_secret"])
        kite_session["access_token"] = data["access_token"]
        kite_session["request_token"] = request_token
        kite_session["user_id"] = data.get("user_id", "")
        kite_session["connected"] = True
        return {
            "status": "connected",
            "user_id": kite_session["user_id"],
            "message": "Successfully connected to Kite. Live data and trading are now available.",
        }
    except ImportError:
        return {"status": "error", "message": "kiteconnect package not installed. Install with: pip install kiteconnect"}
    except Exception as e:
        logger.error(f"Session generation error: {e}")
        return {"status": "error", "message": str(e)}
def get_kite_instance():
    """Get authenticated KiteConnect instance."""
    if not kite_session["connected"]:
        return None
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=kite_session["api_key"])
        kite.set_access_token(kite_session["access_token"])
        return kite
    except Exception:
        return None
def get_kite_quote(symbol: str) -> Optional[dict]:
    """Get live quote from Kite for a symbol."""
    kite = get_kite_instance()
    if not kite:
        return None
    try:
        instrument = f"NSE:{symbol}"
        data = kite.quote([instrument])
        if instrument in data:
            q = data[instrument]
            ohlc = q.get("ohlc", {})
            return {
                "symbol": symbol,
                "name": symbol,
                "ltp": q.get("last_price", 0),
                "change": q.get("net_change", 0),
                "change_percent": round((q.get("net_change", 0) / ohlc.get("close", 1)) * 100, 2) if ohlc.get("close") else 0,
                "open": ohlc.get("open", 0),
                "high": ohlc.get("high", 0),
                "low": ohlc.get("low", 0),
                "close": ohlc.get("close", 0),
                "volume": q.get("volume", 0),
                "timestamp": datetime.now().isoformat(),
                "source": "kite",
            }
        return None
    except Exception as e:
        logger.error(f"Kite quote error for {symbol}: {e}")
        return None
def get_kite_historical(symbol: str, interval: str = "day", days: int = 180) -> Optional[list]:
    """Get historical data from Kite."""
    kite = get_kite_instance()
    if not kite:
        return None
    try:
        instruments = kite.instruments("NSE")
        instrument_token = None
        for inst in instruments:
            if inst["tradingsymbol"] == symbol:
                instrument_token = inst["instrument_token"]
                break
        if not instrument_token:
            return None
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        data = kite.historical_data(instrument_token, from_date, to_date, interval)
        return [
            {
                "date": str(candle["date"]),
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle["volume"],
            }
            for candle in data
        ]
    except Exception as e:
        logger.error(f"Kite historical error for {symbol}: {e}")
        return None
def get_kite_option_chain(symbol: str) -> list:
    """Get option chain from Kite for index/stock."""
    kite = get_kite_instance()
    if not kite:
        return []
    try:
        exchange = "NFO"
        instruments = kite.instruments(exchange)
        # Filter for options of this symbol
        options = [i for i in instruments if i["name"] == symbol and i["instrument_type"] in ("CE", "PE")]
        # Group by expiry and get nearest
        expiries = sorted(set(i["expiry"] for i in options))
        if not expiries:
            return []
        nearest_expiry = expiries[0]
        near_options = [i for i in options if i["expiry"] == nearest_expiry]
        # Get quotes for all near options
        option_symbols = [f"{exchange}:{o['tradingsymbol']}" for o in near_options]
        # Batch quotes (Kite allows up to 500)
        batch_size = 200
        all_quotes = {}
        for i in range(0, len(option_symbols), batch_size):
            batch = option_symbols[i:i + batch_size]
            quotes = kite.quote(batch)
            all_quotes.update(quotes)
        # Build option chain
        strikes = sorted(set(o["strike"] for o in near_options))
        chain = []
        for strike in strikes:
            entry = {
                "strike_price": strike,
                "expiry": str(nearest_expiry),
                "call_oi": 0, "call_change_oi": 0, "call_ltp": 0, "call_volume": 0, "call_iv": None,
                "put_oi": 0, "put_change_oi": 0, "put_ltp": 0, "put_volume": 0, "put_iv": None,
            }
            for o in near_options:
                if o["strike"] == strike:
                    key = f"{exchange}:{o['tradingsymbol']}"
                    q = all_quotes.get(key, {})
                    if o["instrument_type"] == "CE":
                        entry["call_oi"] = q.get("oi", 0)
                        entry["call_change_oi"] = q.get("oi_day_high", 0) - q.get("oi_day_low", 0)
                        entry["call_ltp"] = q.get("last_price", 0)
                        entry["call_volume"] = q.get("volume", 0)
                    elif o["instrument_type"] == "PE":
                        entry["put_oi"] = q.get("oi", 0)
                        entry["put_change_oi"] = q.get("oi_day_high", 0) - q.get("oi_day_low", 0)
                        entry["put_ltp"] = q.get("last_price", 0)
                        entry["put_volume"] = q.get("volume", 0)
            chain.append(entry)
        return chain
    except Exception as e:
        logger.error(f"Kite option chain error for {symbol}: {e}")
        return []
def place_kite_order(
    symbol: str,
    trade_type: str,
    quantity: int,
    price: float = 0,
    order_type: str = "MARKET",
    product: str = "CNC",
    stop_loss: Optional[float] = None,
    target: Optional[float] = None,
) -> dict:
    """Place order via Kite Connect."""
    kite = get_kite_instance()
    if not kite:
        return {"error": "Not connected to Kite. Please configure and login first."}
    try:
        transaction_type = "BUY" if trade_type.upper() == "BUY" else "SELL"
        kite_order_type = "MARKET" if order_type == "MARKET" else "LIMIT"
        order_id = kite.place_order(
            variety="regular",
            exchange="NSE",
            tradingsymbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            product=product,
            order_type=kite_order_type,
            price=price if kite_order_type == "LIMIT" else None,
            trigger_price=stop_loss,
        )
        result = {
            "id": str(order_id),
            "symbol": symbol,
            "trade_type": trade_type,
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
            "status": "PLACED",
            "mode": "LIVE",
            "broker": "zerodha",
            "timestamp": datetime.now().isoformat(),
        }
        # Place SL order if stop_loss specified
        if stop_loss:
            try:
                sl_type = "SELL" if trade_type == "BUY" else "BUY"
                kite.place_order(
                    variety="regular",
                    exchange="NSE",
                    tradingsymbol=symbol,
                    transaction_type=sl_type,
                    quantity=quantity,
                    product=product,
                    order_type="SL",
                    trigger_price=stop_loss,
                    price=stop_loss,
                )
                result["sl_order"] = "placed"
            except Exception as e:
                result["sl_order_error"] = str(e)
        # Place target order if target specified
        if target:
            try:
                tgt_type = "SELL" if trade_type == "BUY" else "BUY"
                kite.place_order(
                    variety="regular",
                    exchange="NSE",
                    tradingsymbol=symbol,
                    transaction_type=tgt_type,
                    quantity=quantity,
                    product=product,
                    order_type="LIMIT",
                    price=target,
                )
                result["target_order"] = "placed"
            except Exception as e:
                result["target_order_error"] = str(e)
        return result
    except Exception as e:
        logger.error(f"Kite order error: {e}")
        return {"error": str(e)}
def get_kite_positions() -> list:
    """Get positions from Kite."""
    kite = get_kite_instance()
    if not kite:
        return []
    try:
        positions = kite.positions()
        result = []
        for p in positions.get("net", []):
            result.append({
                "symbol": p["tradingsymbol"],
                "exchange": p["exchange"],
                "quantity": p["quantity"],
                "average_price": p["average_price"],
                "last_price": p["last_price"],
                "pnl": p["pnl"],
                "product": p["product"],
            })
        return result
    except Exception as e:
        logger.error(f"Kite positions error: {e}")
        return []
def get_kite_orders() -> list:
    """Get orders from Kite."""
    kite = get_kite_instance()
    if not kite:
        return []
    try:
        orders = kite.orders()
        return [
            {
                "id": o["order_id"],
                "symbol": o["tradingsymbol"],
                "trade_type": o["transaction_type"],
                "order_type": o["order_type"],
                "quantity": o["quantity"],
                "price": o.get("average_price", o.get("price", 0)),
                "status": o["status"],
                "timestamp": str(o.get("order_timestamp", "")),
            }
            for o in orders
        ]
    except Exception as e:
        logger.error(f"Kite orders error: {e}")
        return []
def get_kite_status() -> dict:
    """Get Kite connection status."""
    return {
        "connected": kite_session["connected"],
        "user_id": kite_session["user_id"],
        "api_key_configured": bool(kite_session["api_key"]),
        "login_url": kite_session["login_url"],
    }
def disconnect_kite() -> dict:
    """Disconnect from Kite."""
    kite_session.update({
        "connected": False,
        "access_token": "",
        "request_token": "",
        "user_id": "",
    })
    return {"status": "disconnected", "message": "Kite session disconnected."}
