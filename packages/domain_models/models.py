from pydantic import BaseModel, Field


class TipPayload(BaseModel):
    instrument: str
    segment: str = Field(description="EQUITY or OPTION")
    action: str = Field(description="BUY or SELL")
    entry: float
    stop: float
    target: float
    risk_reward: float
    position_size: int
    confidence: float = Field(ge=0.0, le=1.0)
    strategy_id: str
    explanation: str


class PreTradeCheckRequest(BaseModel):
    deployed_capital: float = Field(gt=0)
    total_open_risk_amount: float = 0
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    quantity: int = Field(gt=0)
    daily_realized_loss: float = 0
    max_daily_loss_amount: float = Field(gt=0)
    open_positions_count: int = 0
    max_open_positions: int = Field(gt=0)
    slippage_estimate_bps: int = 0
    max_slippage_bps: int = 25
    is_stale_quote: bool = False


class PaperMetrics(BaseModel):
    trades: int
    profit_factor: float
    max_drawdown_pct: float
    expectancy: float
