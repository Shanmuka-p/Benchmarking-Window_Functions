-- Query 4: Customer Churn Risk (Window Function Version with LAG)
-- Requirement: Identify users who are 'At Risk' (order count in last 30 days < order count in prior 30 days).

WITH user_active AS (
    SELECT DISTINCT user_id 
    FROM orders 
    WHERE created_at >= (CURRENT_DATE - INTERVAL '60 days')
),
user_periods AS (
    SELECT 
        ua.user_id,
        p.period_id
    FROM user_active ua
    CROSS JOIN (VALUES (1), (2)) AS p(period_id)
),
user_counts AS (
    SELECT 
        up.user_id,
        up.period_id,
        COUNT(o.order_id)::int AS order_cnt
    FROM user_periods up
    LEFT JOIN orders o ON o.user_id = up.user_id
      AND (
        (up.period_id = 1 AND o.created_at >= (CURRENT_DATE - INTERVAL '60 days') AND o.created_at < (CURRENT_DATE - INTERVAL '30 days'))
        OR
        (up.period_id = 2 AND o.created_at >= (CURRENT_DATE - INTERVAL '30 days'))
      )
    GROUP BY up.user_id, up.period_id
),
lagged AS (
    SELECT 
        user_id,
        period_id,
        order_cnt AS orders_last_30d,
        LAG(order_cnt) OVER (PARTITION BY user_id ORDER BY period_id ASC) AS orders_prev_30d
    FROM user_counts
)
SELECT 
    user_id,
    orders_last_30d,
    orders_prev_30d
FROM lagged
WHERE period_id = 2 AND orders_last_30d < orders_prev_30d
ORDER BY user_id ASC;
