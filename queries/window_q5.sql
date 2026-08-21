-- Query 5: Revenue Contribution (Window Function Version)
-- Requirement: For every order, calculate its percentage contribution to that user's lifetime total spend.

SELECT 
    order_id,
    user_id,
    ROUND(amount, 2) AS amount,
    ROUND((amount / SUM(amount) OVER (PARTITION BY user_id)) * 100.0, 4) AS lifetime_share_pct
FROM orders
ORDER BY user_id ASC, order_id ASC;
