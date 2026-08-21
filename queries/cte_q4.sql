-- Query 4: Customer Churn Risk (CTE / Join Version)
-- Requirement: Identify users who are 'At Risk' (order count in last 30 days < order count in prior 30 days).

WITH last_30d AS (
    SELECT user_id, COUNT(*)::int AS orders_last_30d
    FROM orders
    WHERE created_at >= (CURRENT_DATE - INTERVAL '30 days')
    GROUP BY user_id
),
prev_30d AS (
    SELECT user_id, COUNT(*)::int AS orders_prev_30d
    FROM orders
    WHERE created_at >= (CURRENT_DATE - INTERVAL '60 days')
      AND created_at < (CURRENT_DATE - INTERVAL '30 days')
    GROUP BY user_id
)
SELECT 
    p.user_id,
    COALESCE(l.orders_last_30d, 0)::int AS orders_last_30d,
    p.orders_prev_30d::int AS orders_prev_30d
FROM prev_30d p
LEFT JOIN last_30d l ON p.user_id = l.user_id
WHERE COALESCE(l.orders_last_30d, 0) < p.orders_prev_30d
ORDER BY p.user_id ASC;
