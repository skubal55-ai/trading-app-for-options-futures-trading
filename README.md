# AI Trading Platform Starter

Local-first monorepo starter for an Indian equities/options automated trading platform.

## What is included

- FastAPI microservices:
  - `api_gateway`
  - `market_data_service`
  - `strategy_service`
  - `risk_service`
  - `execution_service`
  - `paper_sim_service`
  - `notification_service`
  - `analytics_service`
- Broker adapter stubs for major Indian brokers
- Shared domain models and risk utilities
- PostgreSQL-ready SQLAlchemy models + migration SQL
- Free API adapter layer with fallback routing stubs
- Strategy plugin and backtest hook scaffold
- Docker Compose for one-command local startup

## Quick start

1. Copy env file:

```bash
cp .env.example .env
```

Generate an encryption key for broker credentials and set it in `.env`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

2. Start all services:

```bash
docker compose up --build
```

3. Verify:

- API gateway health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- Market data health: `http://localhost:8001/health`

4. Initialize database tables from gateway:

```bash
curl -X POST http://localhost:8000/api/v1/system/db/init
```

## Key endpoints

- `GET /api/v1/tips/sample`
- `POST /api/v1/risk/pretrade-check`
- `POST /api/v1/live/enable`
- `POST /api/v1/system/db/init`
- `GET /options-chain/sample` (market data service)
- `GET /quote/sample` (market data service)
- `GET /news/sample` (market data service)
- `POST /signal/evaluate` (strategy service)
- `POST /backtest/run` (strategy service)
- `POST /brokers/credentials/upsert` (execution service)
- `POST /brokers/{broker}/authenticate` (execution service)
- `POST /orders/execute` (execution service, persists orders)
- `POST /journal/append` (execution service, persists journal)
- `POST /paper-run/record` (paper sim service, auto-updates live gate)
- `GET /api/v1/live/status` (gateway, current live-mode state)
- `POST /alerts/send` (notification service, Telegram/Twilio WhatsApp)
- `POST /api/v1/orchestrate/trade-cycle` (gateway, one-call strategy->risk->execute/paper->journal->alerts)

## Notes

- This is a starter scaffold, not production-ready execution logic.
- Live mode is blocked unless paper-gate conditions pass.
- Add real broker credentials, exchange calendars, and data provider adapters before live use.

### One-call orchestration example

```bash
curl -X POST http://localhost:8000/api/v1/orchestrate/trade-cycle \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "paper",
    "symbol": "NIFTY",
    "strategy_id": "trend_ema_pullback",
    "position_size": 10,
    "broker": "zerodha",
    "deployed_capital": 100000,
    "max_daily_loss_amount": 5000
  }'
```
