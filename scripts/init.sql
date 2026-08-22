-- DDL and Automated Seeding Script for PostgreSQL Analytics Benchmarking Suite

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop tables if they exist (for clean initialization)
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Step 1: Database Schema Design
CREATE TABLE users (
    user_id INT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    cohort_month DATE NOT NULL,
    referred_by INT NULL REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    product_id INT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Step 2: Automated Seeding Strategy
DO $$
DECLARE
    v_start_time TIMESTAMPTZ;
    v_end_time TIMESTAMPTZ;
BEGIN
    v_start_time := clock_timestamp();
    RAISE NOTICE 'Starting database seeding process...';

    -- 1. Seed 200,000 Users
    -- Cohort months range over the last 24 months from 2024-09-01 back to 2022-10-01
    -- referral logic creates acyclic chains: ~30% of users reference an earlier user_id
    INSERT INTO users (user_id, email, cohort_month, referred_by)
    SELECT
        u AS user_id,
        'user_' || u || '@analytics-bench.io' AS email,
        (DATE '2024-09-01' - ((floor(random() * 24)::int) || ' month')::interval)::date AS cohort_month,
        CASE
            WHEN u > 1 AND random() < 0.35 THEN
                -- Target lower user IDs to form deep referral trees stemming from early users
                GREATEST(1, floor(power(random(), 2.5) * (u - 1) + 1)::int)
            ELSE NULL
        END AS referred_by
    FROM generate_series(1, 200000) AS u;

    RAISE NOTICE 'Seeded 200,000 users successfully.';

    -- 2. Seed 1,000,000 Orders
    -- User ID distribution follows Power Law (Zipfian) where top users get thousands of orders
    INSERT INTO orders (order_id, user_id, product_id, amount, status, created_at, updated_at)
    SELECT
        gen_random_uuid() AS order_id,
        GREATEST(1, LEAST(200000, floor(power(random(), 3.8) * 200000 + 1)::int)) AS user_id,
        floor(random() * 500 + 1)::int AS product_id,
        round((random() * 490 + 10)::numeric, 2) AS amount,
        (ARRAY['completed', 'completed', 'completed', 'shipped', 'pending', 'cancelled'])[floor(random() * 6 + 1)] AS status,
        c_at AS created_at,
        c_at + (random() * interval '2 hours') AS updated_at
    FROM (
        SELECT (NOW() - (random() * interval '180 days')) AS c_at
        FROM generate_series(1, 1000000)
    ) sub;

    v_end_time := clock_timestamp();
    RAISE NOTICE 'Seeded 1,000,000 orders successfully in % seconds.', EXTRACT(EPOCH FROM (v_end_time - v_start_time));
END $$;

-- Analyze tables to update PostgreSQL statistics
ANALYZE users;
ANALYZE orders;
