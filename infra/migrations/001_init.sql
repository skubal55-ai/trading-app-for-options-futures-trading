CREATE TABLE IF NOT EXISTS signals (
  id SERIAL PRIMARY KEY,
  instrument VARCHAR(64) NOT NULL,
  segment VARCHAR(16) NOT NULL,
  action VARCHAR(8) NOT NULL,
  entry DOUBLE PRECISION NOT NULL,
  stop DOUBLE PRECISION NOT NULL,
  target DOUBLE PRECISION NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  strategy_id VARCHAR(64) NOT NULL,
  explanation TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_instrument ON signals (instrument);
CREATE INDEX IF NOT EXISTS idx_signals_strategy_id ON signals (strategy_id);

CREATE TABLE IF NOT EXISTS orders (
  id SERIAL PRIMARY KEY,
  broker VARCHAR(32) NOT NULL,
  broker_order_id VARCHAR(96) NOT NULL,
  instrument VARCHAR(64) NOT NULL,
  status VARCHAR(24) NOT NULL,
  quantity INTEGER NOT NULL,
  avg_price DOUBLE PRECISION NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_broker ON orders (broker);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);

CREATE TABLE IF NOT EXISTS trade_journal (
  id SERIAL PRIMARY KEY,
  strategy_id VARCHAR(64) NOT NULL,
  note TEXT NOT NULL,
  pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trade_journal_strategy_id ON trade_journal (strategy_id);

CREATE TABLE IF NOT EXISTS broker_credentials (
  id SERIAL PRIMARY KEY,
  broker VARCHAR(32) NOT NULL UNIQUE,
  encrypted_payload TEXT NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paper_run_metrics (
  id SERIAL PRIMARY KEY,
  strategy_id VARCHAR(64) NOT NULL,
  trades INTEGER NOT NULL,
  profit_factor DOUBLE PRECISION NOT NULL,
  max_drawdown_pct DOUBLE PRECISION NOT NULL,
  expectancy DOUBLE PRECISION NOT NULL,
  gate_status VARCHAR(16) NOT NULL DEFAULT 'unknown',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paper_run_metrics_strategy_id ON paper_run_metrics (strategy_id);

CREATE TABLE IF NOT EXISTS live_mode_state (
  id INTEGER PRIMARY KEY,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  reason TEXT NOT NULL DEFAULT 'Paper gate not evaluated yet',
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO live_mode_state (id, enabled, reason)
VALUES (1, FALSE, 'Paper gate not evaluated yet')
ON CONFLICT (id) DO NOTHING;
