"""db.py — connection pool with retry on startup."""
import os
import time
import psycopg2
from psycopg2 import pool

_pool = None

def _dsn():
    return (
        f"host={os.environ['DB_HOST']} "
        f"port={os.environ.get('DB_PORT', 5432)} "
        f"dbname={os.environ['POSTGRES_DB']} "
        f"user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']}"
    )

def init_pool(retries=10, delay=2):
    """Create the connection pool, retrying until the DB is ready."""
    global _pool
    for attempt in range(1, retries + 1):
        try:
            _pool = pool.SimpleConnectionPool(1, 10, dsn=_dsn())
            return
        except psycopg2.OperationalError as exc:
            if attempt == retries:
                raise
            print(f"[db] connect attempt {attempt}/{retries} failed: {exc}; retrying in {delay}s")
            time.sleep(delay)

def get_conn():
    return _pool.getconn()

def put_conn(conn):
    _pool.putconn(conn)
