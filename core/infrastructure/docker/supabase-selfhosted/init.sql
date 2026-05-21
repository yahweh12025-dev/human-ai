-- Human-AI Swarm Database Schema
-- Self-hosted Supabase initialization

CREATE ROLE anon NOLOGIN;
GRANT USAGE ON SCHEMA public TO anon;

-- Agent events table
CREATE TABLE IF NOT EXISTS agent_events (
    id SERIAL PRIMARY KEY,
    agent VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    data JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    agent VARCHAR(50) NOT NULL,
    symbol VARCHAR(20),
    side VARCHAR(10),
    amount DECIMAL(20, 8),
    price DECIMAL(20, 8),
    pnl DECIMAL(20, 8),
    data JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Task completions
CREATE TABLE IF NOT EXISTS task_completions (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    agent VARCHAR(50),
    status VARCHAR(20) DEFAULT 'completed',
    data JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- System health
CREATE TABLE IF NOT EXISTS system_health (
    id SERIAL PRIMARY KEY,
    metrics JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Social posts
CREATE TABLE IF NOT EXISTS social_posts (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50),
    content_id VARCHAR(200),
    data JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Backtest results
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    agent VARCHAR(50) NOT NULL,
    strategy VARCHAR(100),
    symbol VARCHAR(20),
    timeframe VARCHAR(10),
    start_date DATE,
    end_date DATE,
    net_profit DECIMAL(20, 8),
    win_rate DECIMAL(5, 2),
    profit_factor DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    total_trades INTEGER,
    data JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- EA trade log
CREATE TABLE IF NOT EXISTS ea_trades (
    id SERIAL PRIMARY KEY,
    ea_name VARCHAR(100),
    symbol VARCHAR(20),
    side VARCHAR(10),
    entry_price DECIMAL(20, 5),
    exit_price DECIMAL(20, 5),
    tp DECIMAL(20, 5),
    sl DECIMAL(20, 5),
    pnl DECIMAL(20, 8),
    duration_minutes INTEGER,
    data JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Grant permissions
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO anon;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon;

-- Index for fast queries
CREATE INDEX idx_agent_events_agent ON agent_events(agent);
CREATE INDEX idx_agent_events_timestamp ON agent_events(timestamp);
CREATE INDEX idx_trades_agent ON trades(agent);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_task_completions_agent ON task_completions(agent);
CREATE INDEX idx_backtest_results_agent ON backtest_results(agent);
CREATE INDEX idx_ea_trades_ea_name ON ea_trades(ea_name);
