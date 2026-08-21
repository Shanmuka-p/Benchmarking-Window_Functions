-- Query 1: Rolling Revenue (CTE / Self-Join Version)
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
    d1.day,
    ROUND(d1.daily_revenue, 2) AS daily_revenue,
    ROUND(AVG(d2.daily_revenue), 2) AS rolling_7d_avg
FROM daily_rev d1
JOIN daily_rev d2 ON d2.day BETWEEN (d1.day - INTERVAL '6 days')::date AND d1.day
GROUP BY d1.day, d1.daily_revenue
ORDER BY d1.day ASC;
