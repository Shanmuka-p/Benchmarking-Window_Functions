-- Index Optimization Script for Benchmarking Suite

-- Index 1: B-Tree index on orders(user_id, created_at) for partition sorting & filtering
CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders (user_id, created_at);

-- Index 2: B-Tree index on users(cohort_month) for cohort partition filtering
CREATE INDEX IF NOT EXISTS idx_users_cohort ON users (cohort_month);

-- Index 3: B-Tree index on orders(created_at) for date-range aggregations (Rolling Revenue & Churn Risk)
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders (created_at);

-- Update statistics after creating indices
ANALYZE users;
ANALYZE orders;
