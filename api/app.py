import time

from flask import Flask, Response, abort, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from psycopg2 import errors
from werkzeug.exceptions import HTTPException

import db

app = Flask(__name__)

REQUESTS = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "route", "status"]
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)
EXCLUDED_ROUTES = {"/health", "/metrics"}
MAX_ID = 2147483647

db.connect(retries=10, delay=2).close()


def error(message, status):
    return jsonify({"error": message}), status


def serialize(row):
    return {**row, "created_at": row["created_at"].isoformat()}


def parse_id(raw):
    if not (raw.isascii() and raw.isdigit()) or int(raw) > MAX_ID:
        abort(404)
    return int(raw)


def read_payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    name, email, course = data.get("name"), data.get("email"), data.get("course")
    if not isinstance(name, str) or not name.strip():
        return None
    if not isinstance(email, str) or "@" not in email.strip():
        return None
    if course is not None and not isinstance(course, str):
        return None
    return name.strip(), email.strip(), course


@app.before_request
def start_timer():
    g.start = time.perf_counter()


@app.after_request
def record_metrics(response):
    rule = request.url_rule.rule if request.url_rule else None
    if rule in EXCLUDED_ROUTES:
        return response
    route = rule or "unmatched"
    REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    start = g.get("start")
    if start is not None:
        LATENCY.labels(request.method, route).observe(time.perf_counter() - start)
    return response


@app.errorhandler(HTTPException)
def handle_http_error(exc):
    return error(exc.description, exc.code)


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    app.logger.exception("unhandled error")
    return error("internal server error", 500)


@app.get("/health")
def health():
    try:
        db.ping()
    except Exception:
        app.logger.exception("health check failed")
        return error("database unavailable", 503)
    return jsonify({"status": "ok", "db": "ok"})


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@app.get("/students")
def list_students():
    return jsonify([serialize(row) for row in db.list_students()])


@app.get("/students/<id>")
def get_student(id):
    row = db.get_student(parse_id(id))
    if row is None:
        return error("student not found", 404)
    return jsonify(serialize(row))


@app.post("/students")
def create_student():
    payload = read_payload()
    if payload is None:
        return error("name and email are required; course must be a string", 400)
    try:
        row = db.create_student(*payload)
    except errors.UniqueViolation:
        return error("email already exists", 409)
    return jsonify(serialize(row)), 201


@app.put("/students/<id>")
def update_student(id):
    student_id = parse_id(id)
    payload = read_payload()
    if payload is None:
        return error("name and email are required; course must be a string", 400)
    try:
        row = db.update_student(student_id, *payload)
    except errors.UniqueViolation:
        return error("email already exists", 409)
    if row is None:
        return error("student not found", 404)
    return jsonify(serialize(row))


@app.delete("/students/<id>")
def delete_student(id):
    if db.delete_student(parse_id(id)) is None:
        return error("student not found", 404)
    return "", 204
