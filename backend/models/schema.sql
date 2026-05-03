-- Trading Journal SQLite Schema
-- Apply with: python database.py (called on app startup via init_db())

CREATE TABLE IF NOT EXISTS daily_gainers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    date          TEXT    NOT NULL,
    ticker        TEXT    NOT NULL,
    gap_pct       REAL,
    float_shares  REAL,
    rvol_15m      REAL,
    sector        TEXT,
    market_cap    REAL,
    news_headline TEXT,
    news_fresh    BOOLEAN,
    close_price   REAL,
    open_price    REAL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_gainers_date   ON daily_gainers(date);
CREATE INDEX IF NOT EXISTS idx_gainers_ticker ON daily_gainers(ticker);

CREATE TABLE IF NOT EXISTS chart_captures (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker              TEXT    NOT NULL,
    capture_date        TEXT    NOT NULL,
    timeframe           TEXT,
    image_path          TEXT    NOT NULL,
    setup_type          TEXT,
    cleanliness_score   INTEGER CHECK(cleanliness_score BETWEEN 1 AND 10),
    tags                TEXT,               -- JSON array string, validated server-side
    notes               TEXT,
    -- Gemini vision import fields
    gemini_annotation   TEXT,               -- pasted text from Gemini chat
    gemini_image_path   TEXT,               -- optional annotated image re-uploaded from Gemini
    gemini_imported_at  TIMESTAMP,
    -- Reserved for future local LLM use
    llm_annotation      TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_charts_ticker ON chart_captures(ticker);
CREATE INDEX IF NOT EXISTS idx_charts_date   ON chart_captures(capture_date);

CREATE TABLE IF NOT EXISTS llm_jobs (
    id         TEXT    PRIMARY KEY,          -- UUID
    type       TEXT    NOT NULL,             -- 'continuation' | 'sentiment' | 'news_fresh'
    status     TEXT    DEFAULT 'pending',    -- pending | running | done | error
    input_ref  TEXT,                         -- date string or query snippet
    output     TEXT,
    model_used TEXT,                         -- log which LLM_MODEL produced this
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
