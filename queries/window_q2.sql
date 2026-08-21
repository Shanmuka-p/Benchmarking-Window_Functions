-- Query 2: Cohort Spending Ranks (Window Function Version)
-- Requirement: Rank users by lifetime spend within their signup-month cohort. Return Top 10 spenders for every cohort.

WITH user_spend AS (
    SELECT 
        u.cohort_month,
        u.user_id,
        ROUND(SUM(o.amount), 2) AS total_spend
    FROM users u
    JOIN orders o ON u.user_id = o.user_id
    GROUP BY u.cohort_month, u.user_id
),
ranked_users AS (
    SELECT 
        cohort_month,
        user_id,
        total_spend,
        DENSE_RANK() OVER (
            PARTITION BY cohort_month 
            ORDER BY total_spend DESC, user_id ASC
        )::int AS rank_in_cohort
    FROM user_spend
)
SELECT 
    cohort_month,
    user_id,
    total_spend,
    rank_in_cohort
FROM ranked_users
WHERE rank_in_cohort <= 10
ORDER BY cohort_month DESC, rank_in_cohort ASC, user_id ASC;
