-- Lab Data Product database schema
-- Products table stores the domain entities

CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(255) PRIMARY KEY,
    patient_id VARCHAR(255),
    bundle_id VARCHAR(255),
    pathogen_code VARCHAR(255),
    pathogen_description VARCHAR(255),
    interpretation VARCHAR(255),
    timestamp VARCHAR(255),
    version_number INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_products_pathogen_code ON products(pathogen_code);
CREATE INDEX IF NOT EXISTS idx_products_bundle_id ON products(bundle_id);

-- Metrics table stores the read model for CQRS pattern
-- Updated by event handlers when data products are created
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255),
    pathogen_code VARCHAR(255),
    pathogen_description VARCHAR(255),
    report_timestamp VARCHAR(255),
    created_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_metrics_pathogen_code ON metrics(pathogen_code);
CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON metrics(created_at);
