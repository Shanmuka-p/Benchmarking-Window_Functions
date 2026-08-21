-- Query 5: Revenue Contribution (CTE / Group By Join Version)
-- Requirement: For every order, calculate its percentage contribution to that user's lifetime total spend.

WITH user_totals AS (
    SELECT 
        user_id,
        SUM(amount) AS total_spend
    FROM orders
    GROUP BY user_id
)
SELECT 
    o.order_id,
    o.user_id,
    ROUND(o.amount, 2) AS amount,
    ROUND((o.amount / ut.total_spend) * 100.0, 4) AS lifetime_share_pct
FROM orders o
JOIN user_totals ut ON o.user_id = ut.user_id
ORDER BY o.user_id ASC, o.order_id ASC;
