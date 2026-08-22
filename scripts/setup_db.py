#!/usr/bin/env python3
"""
Database Setup and Seeding Script for Benchmarking Suite
Creates analytics_db database and executes scripts/init.sql to generate 200,000 users and 1,000,000 orders.
"""

import os
import sys
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres_password_123")
DB_NAME = os.getenv("POSTGRES_DB", "analytics_db")

def get_connection(dbname="postgres"):
    candidate_ports = [DEFAULT_PORT, 5433, 5432, 5434]
    passwords_to_try = [DB_PASSWORD, "", "postgres", "postgres_password_123"]

    for port in candidate_ports:
        for password in passwords_to_try:
            try:
                conn_kwargs = {
                    "host": DB_HOST,
                    "port": port,
                    "user": DB_USER,
                    "dbname": dbname
                }
                if password:
                    conn_kwargs["password"] = password
                conn = psycopg2.connect(**conn_kwargs)
                return conn, port
            except Exception:
                continue

    raise psycopg2.OperationalError(
        f"Could not connect to PostgreSQL server on host '{DB_HOST}' using ports {candidate_ports}. "
        "Ensure PostgreSQL server or Docker container is running."
    )

def main():
    print(f"Connecting to PostgreSQL server at {DB_HOST}...")
    
    # Step 1: Connect to default postgres database to create analytics_db if needed
    try:
        conn, resolved_port = get_connection(dbname="postgres")
        print(f"Connected successfully on port {resolved_port}.")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cur.fetchone()
        if not exists:
            print(f"Creating database {DB_NAME}...")
            cur.execute(f"CREATE DATABASE {DB_NAME};")
        else:
            print(f"Database {DB_NAME} already exists.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error checking/creating database: {e}")
        sys.exit(1)

    # Step 2: Connect to analytics_db and run scripts/init.sql
    print(f"Connecting to {DB_NAME} on port {resolved_port}...")
    conn, _ = get_connection(dbname=DB_NAME)
    conn.autocommit = True
    cur = conn.cursor()

    print("Reading scripts/init.sql...")
    with open("scripts/init.sql", "r", encoding="utf-8") as f:
        init_sql = f.read()

    print("Executing database DDL and 1.2M row automated seeding script (this will take ~10-20 seconds)...")
    start_t = time.time()
    cur.execute(init_sql)
    elapsed = time.time() - start_t
    print(f"Database initialization & seeding completed in {elapsed:.2f} seconds!")

    # Step 3: Verify row counts and constraints
    cur.execute("SELECT count(*) FROM users;")
    user_count = cur.fetchone()[0]
    
    cur.execute("SELECT count(*) FROM orders;")
    order_count = cur.fetchone()[0]

    print(f"\n--- Database Seeding Verification ---")
    print(f"Users table count  : {user_count:,} (Required: >= 200,000)")
    print(f"Orders table count : {order_count:,} (Required: >= 1,000,000)")

    if user_count >= 200000 and order_count >= 1000000:
        print("Verification PASSED: All row count requirements satisfied!")
    else:
        print("Verification FAILED: Insufficient row counts!")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
