CREATE TABLE IF NOT EXISTS coins (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ohlcv_prices (
    symbol TEXT NOT NULL REFERENCES coins(symbol),
    price_date DATE NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(30, 8),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, price_date)
);

CREATE TABLE IF NOT EXISTS model_runs (
    id BIGSERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    accuracy NUMERIC(8, 6),
    macro_f1 NUMERIC(8, 6),
    trained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS regime_predictions (
    symbol TEXT NOT NULL REFERENCES coins(symbol),
    price_date DATE NOT NULL,
    regime TEXT NOT NULL,
    confidence NUMERIC(8, 6) NOT NULL,
    model_run_id BIGINT REFERENCES model_runs(id),
    features JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, price_date)
);

CREATE INDEX IF NOT EXISTS idx_regime_predictions_symbol_date
    ON regime_predictions(symbol, price_date DESC);

INSERT INTO coins(symbol, name) VALUES
    ('BTC', 'Bitcoin'),
    ('ETH', 'Ethereum'),
    ('SOL', 'Solana'),
    ('LINK', 'Chainlink'),
    ('DOGE', 'Dogecoin')
ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name;
