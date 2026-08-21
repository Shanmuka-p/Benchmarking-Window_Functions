-- Query 3: Extreme Orders (CTE / Array Aggregation Version)
-- Requirement: For every user, find their very first order and their very last order in a single query result without self-joins.

WITH user_order_arrays AS (
    SELECT 
        user_id,
        (ARRAY_AGG(created_at ORDER BY created_at ASC, order_id ASC))[1] AS first_order_date,
        (ARRAY_AGG(created_at ORDER BY created_at DESC, order_id DESC))[1] AS last_order_date,
        (ARRAY_AGG(amount ORDER BY created_at ASC, order_id ASC))[1] AS first_order_amount,
        (ARRAY_AGG(amount ORDER BY created_at DESC, order_id DESC))[1] AS last_order_amount
    FROM orders
    GROUP BY user_id
)
SELECT 
    user_id,
    first_order_date,
    last_order_date,
    ROUND(first_order_amount, 2) AS first_order_amount,
    ROUND(last_order_amount, 2) AS last_order_amount
FROM user_order_arrays
ORDER BY user_id ASC;
