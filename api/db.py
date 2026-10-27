import os
import time
from contextlib import closing

import psycopg2
from psycopg2.extras import RealDictCursor


def connect(retries=1, delay=2):
    for attempt in range(1, retries + 1):
        try:
            return psycopg2.connect(
                host=os.environ.get("DB_HOST", "db"),
                port=os.environ.get("DB_PORT", "5432"),
                dbname=os.environ.get("POSTGRES_DB", "students"),
                user=os.environ.get("POSTGRES_USER", "student"),
                password=os.environ["POSTGRES_PASSWORD"],
                connect_timeout=2,
                options="-c timezone=UTC",
            )
        except psycopg2.OperationalError:
            if attempt == retries:
                raise
            time.sleep(delay)


def _run(sql, params=(), one=False):
    with closing(connect()) as conn:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if cur.description is None:
                return None
            return cur.fetchone() if one else cur.fetchall()


def ping():
    _run("SELECT 1", one=True)


def list_students():
    return _run("SELECT id, name, email, course, created_at FROM students ORDER BY id")


def get_student(student_id):
    return _run(
        "SELECT id, name, email, course, created_at FROM students WHERE id = %s",
        (student_id,),
        one=True,
    )


def create_student(name, email, course):
    return _run(
        "INSERT INTO students (name, email, course) VALUES (%s, %s, %s) "
        "RETURNING id, name, email, course, created_at",
        (name, email, course),
        one=True,
    )


def update_student(student_id, name, email, course):
    return _run(
        "UPDATE students SET name = %s, email = %s, course = %s WHERE id = %s "
        "RETURNING id, name, email, course, created_at",
        (name, email, course, student_id),
        one=True,
    )


def delete_student(student_id):
    return _run("DELETE FROM students WHERE id = %s RETURNING id", (student_id,), one=True)
