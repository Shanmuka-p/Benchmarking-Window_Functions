-- Query 2: Cohort Spending Ranks (CTE / Lateral Join Version)
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
cohorts AS (
    SELECT DISTINCT cohort_month FROM users
)
SELECT 
    c.cohort_month,
    top_users.user_id,
    top_users.total_spend,
    top_users.rank_in_cohort
FROM cohorts c
CROSS JOIN LATERAL (
    SELECT 
        us.user_id,
        us.total_spend,
        (
            SELECT COUNT(*)::int
            FROM user_spend u2
            WHERE u2.cohort_month = c.cohort_month
              AND (u2.total_spend > us.total_spend 
                   OR (u2.total_spend = us.total_spend AND u2.user_id <= us.user_id))
        ) AS rank_in_cohort
    FROM user_spend us
    WHERE us.cohort_month = c.cohort_month
    ORDER BY us.total_spend DESC, us.user_id ASC
    LIMIT 10
) top_users
ORDER BY c.cohort_month DESC, top_users.rank_in_cohort ASC, top_users.user_id ASC;
