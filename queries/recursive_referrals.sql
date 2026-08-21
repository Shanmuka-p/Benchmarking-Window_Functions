-- Query 8: Recursive Referral Chain Depth
-- Requirement: Find the complete referral chain depth for the top 100 users by order count using WITH RECURSIVE.

WITH RECURSIVE top_100_users AS (
    SELECT user_id
    FROM orders
    GROUP BY user_id
    ORDER BY COUNT(*) DESC, user_id ASC
    LIMIT 100
),
referral_chain AS (
    -- Anchor member: Initialize top 100 users at chain depth 1
    SELECT 
        u.user_id AS root_user_id,
        u.user_id AS current_user_id,
        1 AS chain_depth
    FROM users u
    JOIN top_100_users tu ON u.user_id = tu.user_id

    UNION ALL

    -- Recursive member: Traverse downstream referred users
    SELECT 
        rc.root_user_id,
        u.user_id AS current_user_id,
        rc.chain_depth + 1
    FROM referral_chain rc
    JOIN users u ON u.referred_by = rc.current_user_id
)
SELECT 
    root_user_id AS user_id,
    MAX(chain_depth)::int AS chain_depth
FROM referral_chain
GROUP BY root_user_id
ORDER BY chain_depth DESC, user_id ASC;
