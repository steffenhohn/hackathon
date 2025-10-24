-- Migration 002: Create metrics read model for CQRS pattern
-- Following Cosmic Python pattern: simple append-only table updated by event handlers
-- Aggregations are done in views.py, not pre-computed

-- Metrics read model - one row per DataProductCreated event
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL,
    pathogen_code VARCHAR(255) NOT NULL,
    pathogen_description VARCHAR(255),
    report_timestamp VARCHAR(255) NOT NULL,  -- timestamp from the lab report (specimen collection/analysis)
    created_at TIMESTAMP NOT NULL  -- when the data product was created (from event)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_metrics_pathogen_code
    ON metrics(pathogen_code);

CREATE INDEX IF NOT EXISTS idx_metrics_report_timestamp
    ON metrics(report_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_created_at
    ON metrics(created_at DESC);

-- Composite index for pathogen + time window queries
CREATE INDEX IF NOT EXISTS idx_metrics_pathogen_created_at
    ON metrics(pathogen_code, created_at DESC);
