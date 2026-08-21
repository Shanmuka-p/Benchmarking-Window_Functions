-- Query 1: Rolling Revenue (Window Function Version)
-- Requirement: Calculate the 7-day rolling average revenue per calendar day for the last 90 days.

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
