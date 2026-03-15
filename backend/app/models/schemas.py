from pydantic import BaseModel
from typing import Optional
from enum import Enum


class TradeType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"


class TradingMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"


class Segment(str, Enum):
    EQUITY = "EQUITY"
    OPTIONS = "OPTIONS"
    FUTURES = "FUTURES"


class StrategyType(str, Enum):
    # Equity strategies
    MA_CROSSOVER = "MA_CROSSOVER"
    RSI_DIVERGENCE = "RSI_DIVERGENCE"
    MACD_SIGNAL = "MACD_SIGNAL"
    FIBONACCI_RETRACEMENT = "FIBONACCI_RETRACEMENT"
    BOLLINGER_BREAKOUT = "BOLLINGER_BREAKOUT"
    VWAP_STRATEGY = "VWAP_STRATEGY"
    SUPERTREND = "SUPERTREND"
    PIVOT_POINTS = "PIVOT_POINTS"
    ORDER_BLOCK = "ORDER_BLOCK"
    SUPPLY_DEMAND = "SUPPLY_DEMAND"
    EMA_RIBBON = "EMA_RIBBON"
    VOLUME_BREAKOUT = "VOLUME_BREAKOUT"
    ICT_FVG = "ICT_FVG"
    ORB_STRATEGY = "ORB_STRATEGY"
    # Call-side options buying strategies
    LONG_CALL = "LONG_CALL"
    BULL_CALL_SPREAD = "BULL_CALL_SPREAD"
    LONG_CALL_BUTTERFLY = "LONG_CALL_BUTTERFLY"
    CALL_RATIO_BACKSPREAD = "CALL_RATIO_BACKSPREAD"
    LONG_CALL_CONDOR = "LONG_CALL_CONDOR"
    # Put-side options buying strategies
    LONG_PUT = "LONG_PUT"
    BEAR_PUT_SPREAD = "BEAR_PUT_SPREAD"
    LONG_PUT_BUTTERFLY = "LONG_PUT_BUTTERFLY"
    PUT_RATIO_BACKSPREAD = "PUT_RATIO_BACKSPREAD"
    # Volatility options strategies
    LONG_STRADDLE = "LONG_STRADDLE"
    LONG_STRANGLE = "LONG_STRANGLE"
    # Stock + options combined strategies
    COVERED_CALL = "COVERED_CALL"
    PROTECTIVE_PUT = "PROTECTIVE_PUT"
    COLLAR = "COLLAR"
    SYNTHETIC_LONG = "SYNTHETIC_LONG"
    SYNTHETIC_SHORT = "SYNTHETIC_SHORT"
    STOCK_REPAIR = "STOCK_REPAIR"
    DELTA_NEUTRAL_HEDGE = "DELTA_NEUTRAL_HEDGE"
    # Greeks-based strategies
    DELTA_DIRECTIONAL = "DELTA_DIRECTIONAL"
    GAMMA_SCALPING = "GAMMA_SCALPING"
    IV_CRUSH_PLAY = "IV_CRUSH_PLAY"
    IV_EXPANSION_PLAY = "IV_EXPANSION_PLAY"
    OI_BREAKOUT = "OI_BREAKOUT"
    PCR_REVERSAL = "PCR_REVERSAL"
    MAX_PAIN_MAGNET = "MAX_PAIN_MAGNET"
    GEX_STRATEGY = "GEX_STRATEGY"


class StockQuote(BaseModel):
    symbol: str
    name: str
    ltp: float
    change: float
    change_percent: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: str


class OptionChainEntry(BaseModel):
    strike_price: float
    expiry: str
    call_oi: int
    call_change_oi: int
    call_ltp: float
    call_volume: int
    call_iv: Optional[float] = None
    put_oi: int
    put_change_oi: int
    put_ltp: float
    put_volume: int
    put_iv: Optional[float] = None


class TechnicalIndicators(BaseModel):
    symbol: str
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None
    atr: Optional[float] = None
    adx: Optional[float] = None
    supertrend: Optional[float] = None
    supertrend_direction: Optional[str] = None
    vwap: Optional[float] = None
    stochastic_k: Optional[float] = None
    stochastic_d: Optional[float] = None


class FibonacciLevels(BaseModel):
    symbol: str
    trend: str
    level_0: float
    level_236: float
    level_382: float
    level_500: float
    level_618: float
    level_786: float
    level_1: float


class ScreenerResult(BaseModel):
    symbol: str
    name: str
    ltp: float
    signal: str
    strategy: str
    entry_price: float
    target: float
    stop_loss: float
    risk_reward: float
    confidence: float
    segment: str
    reason: str


class TradeOrder(BaseModel):
    symbol: str
    trade_type: TradeType
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    segment: Segment = Segment.EQUITY
    mode: TradingMode = TradingMode.PAPER


class TradePosition(BaseModel):
    id: str
    symbol: str
    trade_type: TradeType
    entry_price: float
    current_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    segment: str
    mode: str
    status: str
    timestamp: str


class AutoTradeSettings(BaseModel):
    enabled: bool = False
    mode: TradingMode = TradingMode.PAPER
    strategies: list[StrategyType] = []
    max_trades_per_day: int = 5
    max_capital_per_trade: float = 10000.0
    stop_loss_percent: float = 2.0
    target_percent: float = 4.0
    segments: list[Segment] = [Segment.EQUITY]
    trading_start_time: str = "09:15"
    trading_end_time: str = "15:15"


class MarketOverview(BaseModel):
    nifty50: Optional[StockQuote] = None
    nifty_bank: Optional[StockQuote] = None
    nifty_it: Optional[StockQuote] = None
    nifty_fin_service: Optional[StockQuote] = None
    india_vix: Optional[float] = None
    market_status: str = "CLOSED"
    top_gainers: list[StockQuote] = []
    top_losers: list[StockQuote] = []
    most_active: list[StockQuote] = []
