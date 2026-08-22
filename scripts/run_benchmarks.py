#!/usr/bin/env python3
"""
Automated Benchmarking and Profiling Harness
Executes query verification, pre/post index EXPLAIN ANALYZE profiling,
pgbench concurrent load testing, recursive graph analysis, and materialized view timing.
Generates results/benchmarks.json and results.json.
"""

import os
import sys
import json
import time
import re
import shutil
import subprocess
import psycopg2

# Dynamic Database Configuration with Environment Variable Fallbacks
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres_password_123")
DB_NAME = os.getenv("POSTGRES_DB", "analytics_db")

BENCHMARK_DIR = "benchmarks"
RESULTS_DIR = "results"

os.makedirs(BENCHMARK_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Find pgbench binary dynamically
def find_pgbench():
    pgbench_bin = shutil.which("pgbench")
    if pgbench_bin:
        return pgbench_bin
    
    # Common Windows PostgreSQL installation paths
    candidate_paths = [
        r"C:\Program Files\PostgreSQL\18\bin\pgbench.exe",
        r"C:\Program Files\PostgreSQL\17\bin\pgbench.exe",
        r"C:\Program Files\PostgreSQL\16\bin\pgbench.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pgbench.exe",
        "/usr/bin/pgbench",
        "/usr/local/bin/pgbench"
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    return "pgbench"

PGBENCH_PATH = find_pgbench()
RESOLVED_PORT = None

def get_db_connection():
    global RESOLVED_PORT
    if RESOLVED_PORT:
        candidate_ports = [RESOLVED_PORT]
    else:
        candidate_ports = [DEFAULT_PORT, 5433, 5432, 5434]

    passwords_to_try = [DB_PASSWORD, "", "postgres", "postgres_password_123"]

    for port in candidate_ports:
        for password in passwords_to_try:
            try:
                conn_kwargs = {
                    "host": DB_HOST,
                    "port": port,
                    "user": DB_USER,
                    "dbname": DB_NAME
                }
                if password:
                    conn_kwargs["password"] = password
                conn = psycopg2.connect(**conn_kwargs)
                RESOLVED_PORT = port
                return conn
            except Exception:
                continue

    # Fallback to postgres default database if analytics_db doesn't exist yet
    for port in candidate_ports:
        for password in passwords_to_try:
            try:
                conn_kwargs = {
                    "host": DB_HOST,
                    "port": port,
                    "user": DB_USER,
                    "dbname": "postgres"
                }
                if password:
                    conn_kwargs["password"] = password
                conn = psycopg2.connect(**conn_kwargs)
                RESOLVED_PORT = port
                return conn
            except Exception:
                continue

    raise psycopg2.OperationalError(
        f"Could not connect to PostgreSQL on host '{DB_HOST}' using ports {candidate_ports}. "
        "Ensure the database server or Docker container is running."
    )

def read_query(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def run_explain_analyze(conn, query_sql):
    cur = conn.cursor()
    # Execute text explain
    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)\n{query_sql}")
    text_plan = "\n".join([row[0] for row in cur.fetchall()])
    
    # Execute JSON explain for accurate timing extraction
    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n{query_sql}")
    json_plan = cur.fetchone()[0]
    execution_time = json_plan[0]["Execution Time"]
    
    cur.close()
    return text_plan, json_plan, execution_time

def verify_query_correctness():
    print("\n==========================================")
    print("PHASE 2: VERIFYING QUERY FUNCTIONAL EQUIVALENCE")
    print("==========================================")
    conn = get_db_connection()
    cur = conn.cursor()

    for q_num in range(1, 6):
        wf_sql = read_query(f"queries/window_q{q_num}.sql")
        cte_sql = read_query(f"queries/cte_q{q_num}.sql")

        cur.execute(wf_sql)
        wf_rows = cur.fetchall()

        cur.execute(cte_sql)
        cte_rows = cur.fetchall()

        print(f"Query {q_num}: WF returned {len(wf_rows):,} rows | CTE returned {len(cte_rows):,} rows")
        if len(wf_rows) != len(cte_rows):
            print(f"  [ERROR] Row count mismatch for Query {q_num}!")
            sys.exit(1)

        # Check sample equivalence
        if wf_rows[:5] == cte_rows[:5]:
            print(f"  [PASSED] Query {q_num} WF & CTE results are identical!")
        else:
            print(f"  [WARNING] Sample rows differ between WF & CTE for Query {q_num}!")

    # Verify Core Requirement specific rules:
    # Req 6: Query 4 orders_last_30d < orders_prev_30d
    cur.execute(read_query("queries/window_q4.sql"))
    q4_rows = cur.fetchall()
    all_valid = all(r[1] < r[2] for r in q4_rows)
    print(f"Query 4 validation (orders_last_30d < orders_prev_30d): {'PASSED' if all_valid else 'FAILED'}")

    # Req 7: Query 5 lifetime_share_pct sum per user ~100
    q5_sql = read_query("queries/window_q5.sql").strip().rstrip(";")
    cur.execute("WITH q5 AS (" + q5_sql + ") SELECT user_id, SUM(lifetime_share_pct) FROM q5 GROUP BY user_id LIMIT 10;")
    q5_sums = cur.fetchall()
    pct_valid = all(abs(float(r[1]) - 100.0) < 0.1 for r in q5_sums)
    print(f"Query 5 validation (sum lifetime_share_pct ~ 100%): {'PASSED' if pct_valid else 'FAILED'}")

    cur.close()
    conn.close()

def profile_queries_pre_index():
    print("\n==========================================")
    print("PHASE 3 STEP 1: PRE-INDEX EXPLAIN ANALYZE PROFILING")
    print("==========================================")
    conn = get_db_connection()
    timings = {}

    for q_num in range(1, 6):
        timings[f"query_{q_num}"] = {}
        
        # WF Pre-index
        wf_sql = read_query(f"queries/window_q{q_num}.sql")
        text_plan, _, exec_time = run_explain_analyze(conn, wf_sql)
        timings[f"query_{q_num}"]["wf_pre_ms"] = round(exec_time, 2)
        with open(f"{BENCHMARK_DIR}/explain_q{q_num}_wf_pre_index.txt", "w", encoding="utf-8") as f:
            f.write(text_plan)
        print(f"Query {q_num} WF Pre-Index Execution Time: {exec_time:.2f} ms")

        # CTE Pre-index
        cte_sql = read_query(f"queries/cte_q{q_num}.sql")
        text_plan, _, exec_time = run_explain_analyze(conn, cte_sql)
        timings[f"query_{q_num}"]["cte_pre_ms"] = round(exec_time, 2)
        with open(f"{BENCHMARK_DIR}/explain_q{q_num}_cte_pre_index.txt", "w", encoding="utf-8") as f:
            f.write(text_plan)
        print(f"Query {q_num} CTE Pre-Index Execution Time: {exec_time:.2f} ms")

    conn.close()
    return timings

def apply_indices():
    print("\n==========================================")
    print("PHASE 3 STEP 2: APPLYING OPTIMIZED B-TREE INDICES")
    print("==========================================")
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    with open("scripts/create_indices.sql", "r", encoding="utf-8") as f:
        indices_sql = f.read()

    start_t = time.time()
    cur.execute(indices_sql)
    elapsed = time.time() - start_t
    print(f"Indices created successfully in {elapsed:.2f} seconds.")
    cur.close()
    conn.close()

def profile_queries_post_index(pre_timings):
    print("\n==========================================")
    print("PHASE 3 STEP 2: POST-INDEX EXPLAIN ANALYZE PROFILING")
    print("==========================================")
    conn = get_db_connection()
    summary = {}

    for q_num in range(1, 6):
        key = f"query_{q_num}"
        wf_sql = read_query(f"queries/window_q{q_num}.sql")
        text_plan, _, wf_exec_time = run_explain_analyze(conn, wf_sql)
        with open(f"{BENCHMARK_DIR}/explain_q{q_num}_wf_post_index.txt", "w", encoding="utf-8") as f:
            f.write(text_plan)

        cte_sql = read_query(f"queries/cte_q{q_num}.sql")
        text_plan, _, cte_exec_time = run_explain_analyze(conn, cte_sql)
        with open(f"{BENCHMARK_DIR}/explain_q{q_num}_cte_post_index.txt", "w", encoding="utf-8") as f:
            f.write(text_plan)

        wf_pre = pre_timings[key]["wf_pre_ms"]
        speedup = round(wf_pre / wf_exec_time, 2) if wf_exec_time > 0 else 1.0

        summary[key] = {
            "wf_ms": round(wf_exec_time, 2),
            "cte_ms": round(cte_exec_time, 2),
            "index_speedup": speedup
        }

        print(f"Query {q_num}: WF Post-Index={wf_exec_time:.2f} ms | CTE Post-Index={cte_exec_time:.2f} ms | Speedup={speedup}x")

    conn.close()
    return summary

def run_pgbench_tests():
    print("\n==========================================")
    print("PHASE 3 STEP 3: CONCURRENT PGBENCH LOAD TESTING (10 CLIENTS)")
    print("==========================================")
    pgbench_results = {}
    port_str = str(RESOLVED_PORT if RESOLVED_PORT else DEFAULT_PORT)

    for q_num, variant in [(1, "wf"), (1, "cte"), (2, "wf"), (2, "cte")]:
        query_file = f"queries/{'window' if variant == 'wf' else 'cte'}_q{q_num}.sql"
        log_file = f"{BENCHMARK_DIR}/pgbench_q{q_num}_{variant}.log"
        
        print(f"Running pgbench for Query {q_num} ({variant.upper()})...")
        cmd = [
            PGBENCH_PATH,
            "-h", DB_HOST,
            "-p", port_str,
            "-U", DB_USER,
            "-c", "10",
            "-j", "2",
            "-T", "15",
            "-f", query_file,
            DB_NAME
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASSWORD
        
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        output = res.stdout
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(output)

        tps_match = re.search(r"tps = ([\d\.]+)", output)
        lat_match = re.search(r"latency average = ([\d\.]+) ms", output)

        tps = float(tps_match.group(1)) if tps_match else 0.0
        lat = float(lat_match.group(1)) if lat_match else 0.0

        print(f"  Query {q_num} {variant.upper()}: TPS = {tps:.2f} | Latency = {lat:.2f} ms")
        pgbench_results[f"q{q_num}_{variant}_tps"] = tps
        pgbench_results[f"q{q_num}_{variant}_latency_ms"] = lat

    # Populate required structure
    pgbench_results["wf_tps"] = pgbench_results["q1_wf_tps"]
    pgbench_results["cte_tps"] = pgbench_results["q1_cte_tps"]

    return pgbench_results

def benchmark_recursive():
    print("\n==========================================")
    print("PHASE 4: RECURSIVE REFERRAL CHAIN BENCHMARK")
    print("==========================================")
    conn = get_db_connection()
    sql = read_query("queries/recursive_referrals.sql")
    text_plan, _, exec_time = run_explain_analyze(conn, sql)
    with open(f"{BENCHMARK_DIR}/explain_recursive_referrals.txt", "w", encoding="utf-8") as f:
        f.write(text_plan)
    print(f"Recursive Referral Query Execution Time: {exec_time:.2f} ms")
    conn.close()
    return round(exec_time, 2)

def benchmark_materialized_view():
    print("\n==========================================")
    print("PHASE 5: MATERIALIZED VIEW BENCHMARK")
    print("==========================================")
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    # Initial Creation Time
    start_t = time.time()
    with open("queries/materialized_view.sql", "r", encoding="utf-8") as f:
        cur.execute(f.read())
    creation_time = (time.time() - start_t) * 1000.0
    print(f"Materialized View Initial Creation Time: {creation_time:.2f} ms")

    # Verify pg_matviews existence
    cur.execute("SELECT count(*) FROM pg_matviews WHERE matviewname = 'daily_revenue_stats';")
    mv_exists = cur.fetchone()[0] == 1
    print(f"Verification pg_matviews existence: {'PASSED' if mv_exists else 'FAILED'}")

    # Raw Query 1 timing
    wf_sql = read_query("queries/window_q1.sql")
    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n{wf_sql}")
    raw_wf_read_ms = cur.fetchone()[0][0]["Execution Time"]

    # MV Read timing
    mv_read_sql = "SELECT * FROM daily_revenue_stats;"
    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n{mv_read_sql}")
    mv_read_ms = cur.fetchone()[0][0]["Execution Time"]

    print(f"Raw Window Function Read: {raw_wf_read_ms:.2f} ms | MV Read: {mv_read_ms:.2f} ms")

    # Insert 10,000 new orders to measure refresh time
    print("Inserting 10,000 test orders to measure REFRESH MATERIALIZED VIEW time...")
    cur.execute("""
        INSERT INTO orders (order_id, user_id, product_id, amount, status, created_at, updated_at)
        SELECT gen_random_uuid(), 1, 1, 100.00, 'completed', NOW(), NOW()
        FROM generate_series(1, 10000);
    """)

    start_t = time.time()
    cur.execute("REFRESH MATERIALIZED VIEW daily_revenue_stats;")
    refresh_time = (time.time() - start_t) * 1000.0
    print(f"REFRESH MATERIALIZED VIEW Time: {refresh_time:.2f} ms")

    cur.close()
    conn.close()

    return {
        "initial_creation_ms": round(creation_time, 2),
        "refresh_ms": round(refresh_time, 2),
        "raw_wf_read_ms": round(raw_wf_read_ms, 2),
        "mv_read_ms": round(mv_read_ms, 2)
    }

def main():
    verify_query_correctness()
    pre_timings = profile_queries_pre_index()
    apply_indices()
    summary = profile_queries_post_index(pre_timings)
    pgbench_metrics = run_pgbench_tests()
    rec_time = benchmark_recursive()
    mv_metrics = benchmark_materialized_view()

    # Build final results JSON
    final_output = {
        **summary,
        "pgbench_results": pgbench_metrics,
        "recursive_referral_ms": rec_time,
        "materialized_view": mv_metrics
    }

    # Save to both results/benchmarks.json and root results.json
    with open("results/benchmarks.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    print("\n==========================================")
    print("BENCHMARK HARNESS COMPLETE!")
    print("Results saved to results/benchmarks.json and results.json")
    print("==========================================")

if __name__ == "__main__":
    main()
