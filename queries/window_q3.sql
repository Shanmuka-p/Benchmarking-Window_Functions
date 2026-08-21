-- Query 3: Extreme Orders (Window Function Version)
-- Requirement: For every user, find their very first order and their very last order in a single query result without self-joins.

WITH ranked_orders AS (
    SELECT 
        user_id,
        created_at,
        amount,
        FIRST_VALUE(created_at) OVER w AS first_order_date,
        LAST_VALUE(created_at) OVER w AS last_order_date,
        FIRST_VALUE(amount) OVER w AS first_order_amount,
        LAST_VALUE(amount) OVER w AS last_order_amount,
        ROW_NUMBER() OVER w AS rn
    FROM orders
    WINDOW w AS (
        PARTITION BY user_id 
        ORDER BY created_at ASC, order_id ASC 
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    )
)
SELECT 
    user_id,
    first_order_date,
    last_order_date,
    ROUND(first_order_amount, 2) AS first_order_amount,
    ROUND(last_order_amount, 2) AS last_order_amount
FROM ranked_orders
WHERE rn = 1
ORDER BY user_id ASC;
