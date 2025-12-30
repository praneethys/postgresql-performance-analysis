-- Benchmark Queries for Performance Testing

-- These queries simulate real-world scenarios on the events table

-- Query 1: Recent events for a specific user (common pattern)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT *
FROM events
WHERE user_id = 12345
  AND event_time >= NOW() - INTERVAL '7 days'
ORDER BY event_time DESC
LIMIT 100;

-- Query 2: Aggregation by event type over time range
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT
    event_type,
    DATE_TRUNC('hour', event_time) AS hour,
    COUNT(*) AS event_count,
    SUM(revenue) AS total_revenue,
    COUNT(DISTINCT user_id) AS unique_users
FROM events
WHERE event_time >= NOW() - INTERVAL '24 hours'
GROUP BY event_type, DATE_TRUNC('hour', event_time)
ORDER BY hour DESC, event_count DESC;

-- Query 3: Top products by revenue (requires scanning large dataset)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT
    product_id,
    COUNT(*) AS purchase_count,
    SUM(revenue) AS total_revenue,
    AVG(revenue) AS avg_revenue
FROM events
WHERE event_type = 'purchase'
  AND event_time >= NOW() - INTERVAL '30 days'
  AND product_id IS NOT NULL
GROUP BY product_id
ORDER BY total_revenue DESC
LIMIT 50;

-- Query 4: User activity funnel analysis
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT
    COUNT(DISTINCT CASE WHEN event_type = 'page_view' THEN user_id END) AS page_views,
    COUNT(DISTINCT CASE WHEN event_type = 'add_to_cart' THEN user_id END) AS add_to_cart,
    COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS purchases,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN event_type = 'add_to_cart' THEN user_id END) /
        NULLIF(COUNT(DISTINCT CASE WHEN event_type = 'page_view' THEN user_id END), 0),
        2
    ) AS cart_conversion_rate,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) /
        NULLIF(COUNT(DISTINCT CASE WHEN event_type = 'add_to_cart' THEN user_id END), 0),
        2
    ) AS purchase_conversion_rate
FROM events
WHERE event_time >= NOW() - INTERVAL '7 days';

-- Query 5: Geographic distribution of events
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT
    country_code,
    city,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_id) AS unique_users,
    SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS purchases
FROM events
WHERE event_time >= NOW() - INTERVAL '7 days'
GROUP BY country_code, city
ORDER BY event_count DESC
LIMIT 100;

-- Query 6: Time-series data retrieval (common dashboard query)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT
    DATE_TRUNC('day', event_time) AS day,
    event_type,
    COUNT(*) AS event_count
FROM events
WHERE event_time >= NOW() - INTERVAL '90 days'
GROUP BY DATE_TRUNC('day', event_time), event_type
ORDER BY day DESC, event_type;

-- Query 7: Session analysis with JSONB
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT
    session_id,
    COUNT(*) AS events_in_session,
    MIN(event_time) AS session_start,
    MAX(event_time) AS session_end,
    MAX(event_time) - MIN(event_time) AS session_duration,
    jsonb_agg(
        jsonb_build_object(
            'event_type', event_type,
            'event_time', event_time,
            'product_id', product_id
        ) ORDER BY event_time
    ) AS session_events
FROM events
WHERE event_time >= NOW() - INTERVAL '1 day'
  AND session_id IS NOT NULL
GROUP BY session_id
HAVING COUNT(*) > 1
ORDER BY session_duration DESC
LIMIT 100;

-- Query 8: Point lookup by ID (should be fast with primary key)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT *
FROM events
WHERE id = 1000000;

-- Query 9: Range scan on indexed column
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT COUNT(*)
FROM events
WHERE event_time BETWEEN '2024-01-01' AND '2024-01-31';

-- Query 10: Complex join simulation (self-join for user comparison)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT
    e1.user_id,
    COUNT(DISTINCT e1.product_id) AS products_viewed,
    COUNT(DISTINCT e2.product_id) AS products_purchased,
    SUM(e2.revenue) AS total_spent
FROM events e1
LEFT JOIN events e2
    ON e1.user_id = e2.user_id
    AND e2.event_type = 'purchase'
    AND e2.event_time >= NOW() - INTERVAL '30 days'
WHERE e1.event_type = 'page_view'
  AND e1.event_time >= NOW() - INTERVAL '30 days'
GROUP BY e1.user_id
HAVING COUNT(DISTINCT e1.product_id) > 5
LIMIT 100;

-- Comparative queries for partitioned vs non-partitioned tables

-- Compare: Recent data query
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT COUNT(*)
FROM events_partitioned
WHERE event_time >= NOW() - INTERVAL '7 days';

EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT COUNT(*)
FROM events
WHERE event_time >= NOW() - INTERVAL '7 days';

-- Compare: Old data query
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT COUNT(*)
FROM events_partitioned
WHERE event_time BETWEEN '2024-01-01' AND '2024-01-31';

EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT COUNT(*)
FROM events
WHERE event_time BETWEEN '2024-01-01' AND '2024-01-31';

-- Compare: Aggregation across all data
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT
    event_type,
    COUNT(*) AS total_events
FROM events_partitioned
GROUP BY event_type;

EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT
    event_type,
    COUNT(*) AS total_events
FROM events
GROUP BY event_type;
