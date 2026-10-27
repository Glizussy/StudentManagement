"""app.py — Flask Student API with Prometheus metrics."""
import json
import time
from flask import Flask, request, jsonify, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import db as database

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Prometheus metrics (CONTRACT section 6)
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5],
)
IN_FLIGHT = Gauge("http_requests_in_flight", "HTTP requests currently in flight")

EXCLUDED_PATHS = {"/health", "/metrics"}


@app.before_request
def before():
    if request.path not in EXCLUDED_PATHS:
        IN_FLIGHT.inc()
        request._prom_start = time.perf_counter()


@app.after_request
def after(response):
    if request.path not in EXCLUDED_PATHS:
        IN_FLIGHT.dec()
        REQUEST_COUNT.labels(
            method=request.method, route=_route(), status=str(response.status_code)
        ).inc()
        if hasattr(request, "_prom_start"):
            duration = time.perf_counter() - request._prom_start
            REQUEST_LATENCY.labels(
                method=request.method, route=_route()
            ).observe(duration)
    return response


def _route():
    """Return the Flask route template (low-cardinality)."""
    if request.url_rule:
        return request.url_rule.rule
    return request.path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _row_to_dict(row):
    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "course": row[3],
        "created_at": row[4].isoformat(),
    }


def _with_conn(fn):
    conn = database.get_conn()
    try:
        return fn(conn)
    finally:
        database.put_conn(conn)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/health")
def health():
    try:
        def check(conn):
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        _with_conn(check)
        db_status = "ok"
    except Exception:
        db_status = "error"
    return jsonify({"status": "ok", "db": db_status}), 200


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/students", methods=["GET"])
def list_students():
    def query(conn):
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, email, course, created_at FROM students ORDER BY id")
            return [_row_to_dict(r) for r in cur.fetchall()]
    return jsonify(_with_conn(query)), 200


@app.route("/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    def query(conn):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, course, created_at FROM students WHERE id = %s",
                (student_id,),
            )
            return cur.fetchone()
    row = _with_conn(query)
    if row is None:
        return jsonify({"error": "student not found"}), 404
    return jsonify(_row_to_dict(row)), 200


@app.route("/students", methods=["POST"])
def create_student():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    course = data.get("course", "").strip()
    if not name or not email:
        return jsonify({"error": "name and email are required"}), 400

    def insert(conn):
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO students (name, email, course) VALUES (%s, %s, %s) "
                    "RETURNING id, name, email, course, created_at",
                    (name, email, course or None),
                )
                conn.commit()
                return cur.fetchone()
            except Exception as exc:
                conn.rollback()
                raise exc

    try:
        row = _with_conn(insert)
    except Exception as exc:
        if "unique" in str(exc).lower():
            return jsonify({"error": "email already exists"}), 409
        return jsonify({"error": str(exc)}), 500
    return jsonify(_row_to_dict(row)), 201


@app.route("/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    course = data.get("course", "").strip()

    def update(conn):
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE students SET name = COALESCE(NULLIF(%s,''), name), "
                "email = COALESCE(NULLIF(%s,''), email), "
                "course = COALESCE(NULLIF(%s,''), course) "
                "WHERE id = %s "
                "RETURNING id, name, email, course, created_at",
                (name or None, email or None, course or None, student_id),
            )
            conn.commit()
            return cur.fetchone()

    row = _with_conn(update)
    if row is None:
        return jsonify({"error": "student not found"}), 404
    return jsonify(_row_to_dict(row)), 200


@app.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    def delete(conn):
        with conn.cursor() as cur:
            cur.execute("DELETE FROM students WHERE id = %s RETURNING id", (student_id,))
            conn.commit()
            return cur.fetchone()

    row = _with_conn(delete)
    if row is None:
        return jsonify({"error": "student not found"}), 404
    return Response(status=204)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
database.init_pool()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
