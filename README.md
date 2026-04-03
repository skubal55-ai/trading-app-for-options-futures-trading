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

## Notes

- This is a starter scaffold, not production-ready execution logic.
- Live mode is blocked unless paper-gate conditions pass.
- Add real broker credentials, exchange calendars, and data provider adapters before live use.
