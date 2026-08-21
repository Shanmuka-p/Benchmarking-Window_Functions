-- Materialized View Implementation for Query 1 Logic
-- Requirement: Create a materialized view named daily_revenue_stats based on the 7-day rolling revenue logic.

DROP MATERIALIZED VIEW IF EXISTS daily_revenue_stats CASCADE;

CREATE MATERIALIZED VIEW daily_revenue_stats AS
WITH daily_rev AS (
    SELECT 
        created_at::date AS day,
        SUM(amount) AS daily_revenue
    FROM orders
    WHERE created_at >= (CURRENT_DATE - INTERVAL '90 days')
    GROUP BY created_at::date
)
SELECT 
    day,
    ROUND(daily_revenue, 2) AS daily_revenue,
    ROUND(AVG(daily_revenue) OVER (
        ORDER BY day 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7d_avg
FROM daily_rev
ORDER BY day ASC;

-- Unique index to support concurrent refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_revenue_stats_day ON daily_revenue_stats (day);
