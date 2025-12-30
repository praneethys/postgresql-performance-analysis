-- Schema for Performance Analysis Simulation
-- This simulates a real-world scenario: an e-commerce events table growing rapidly

-- Drop existing objects if they exist
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS events_partitioned CASCADE;

-- Main events table (non-partitioned version for comparison)
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMP NOT NULL DEFAULT NOW(),
    user_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    product_id BIGINT,
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    country_code CHAR(2),
    city VARCHAR(100),
    revenue NUMERIC(10, 2),
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes on the non-partitioned table
CREATE INDEX idx_events_event_time ON events(event_time);
CREATE INDEX idx_events_user_id ON events(user_id);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_product_id ON events(product_id) WHERE product_id IS NOT NULL;

-- Partitioned version of the table (for comparison)
CREATE TABLE events_partitioned (
    id BIGSERIAL,
    event_time TIMESTAMP NOT NULL DEFAULT NOW(),
    user_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    product_id BIGINT,
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    country_code CHAR(2),
    city VARCHAR(100),
    revenue NUMERIC(10, 2),
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (event_time);

-- Create partitions for the last 12 months
DO $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    FOR i IN 0..11 LOOP
        start_date := DATE_TRUNC('month', CURRENT_DATE - INTERVAL '11 months') + (i || ' months')::INTERVAL;
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'events_partitioned_' || TO_CHAR(start_date, 'YYYY_MM');

        EXECUTE FORMAT(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF events_partitioned
             FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );

        -- Create indexes on each partition
        EXECUTE FORMAT('CREATE INDEX IF NOT EXISTS %I ON %I(event_time)',
                      partition_name || '_event_time_idx', partition_name);
        EXECUTE FORMAT('CREATE INDEX IF NOT EXISTS %I ON %I(user_id)',
                      partition_name || '_user_id_idx', partition_name);
        EXECUTE FORMAT('CREATE INDEX IF NOT EXISTS %I ON %I(event_type)',
                      partition_name || '_event_type_idx', partition_name);
    END LOOP;
END $$;

-- Table to track performance metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(200) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    row_count BIGINT,
    query TEXT,
    execution_time_ms NUMERIC(10, 2),
    plan_time_ms NUMERIC(10, 2),
    buffers_hit BIGINT,
    buffers_read BIGINT,
    test_timestamp TIMESTAMP DEFAULT NOW(),
    notes TEXT
);

-- View to check table bloat
CREATE OR REPLACE VIEW table_bloat AS
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size,
    ROUND(100 * pg_total_relation_size(schemaname||'.'||tablename)::numeric /
          NULLIF(pg_database_size(current_database()), 0), 2) AS pct_of_db
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- View to monitor index usage
CREATE OR REPLACE VIEW index_usage AS
SELECT
    schemaname,
    relname AS tablename,
    indexrelname AS indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    CASE
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 100 THEN 'LOW USAGE'
        ELSE 'ACTIVE'
    END AS usage_status
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC;

COMMENT ON TABLE events IS 'Non-partitioned events table for performance comparison';
COMMENT ON TABLE events_partitioned IS 'Partitioned events table using range partitioning by event_time';
COMMENT ON TABLE performance_metrics IS 'Stores benchmark results for analysis';
