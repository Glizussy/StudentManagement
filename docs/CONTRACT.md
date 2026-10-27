# SHARED CONTRACT — Student API + Monitoring Stack

Status: **FROZEN at G0.** Changes to any value below require all three members to agree and a one-line entry in `docs/NOTES.md`.
Owners: A = app layer, B = observability, C = orchestration/demo.

---

## 1. Services, images, ports

| Service | Image / build | Internal port | Host exposure (dev) | Host exposure (prod) |
|---|---|---|---|---|
| `api` | `build: ./api` (python:3.12-slim multi-stage) | 5000 | 5000 | 5000 |
| `db` | `postgres:16.4-alpine` | 5432 | 5432 | **none** |
| `prometheus` | `prom/prometheus:v2.53.0` | 9090 | 9090 | **none** |
| `grafana` | `grafana/grafana:11.1.0` | 3000 | 3000 | 3000 |

- No `latest` tags anywhere.
- Service names are **DNS hostnames** on `app-net`. Never use `localhost` between containers, never hardcode IPs.
- Compose v2 only: `docker compose`, not `docker-compose`.

## 2. Network, volumes

| Kind | Name | Purpose |
|---|---|---|
| network | `app-net` (bridge) | all four services |
| volume | `pgdata` → `/var/lib/postgresql/data` | DB persistence |
| volume | `prom-data` → `/prometheus` | Prometheus TSDB |
| volume | `grafana-data` → `/var/lib/grafana` | Grafana state |

## 3. Environment variables (single source of truth: `.env`)

`.env` is gitignored; `.env.example` is committed with exactly these keys.

| Key | Value | Consumer |
|---|---|---|
| `POSTGRES_DB` | `students` | db, api |
| `POSTGRES_USER` | `student` | db, api |
| `POSTGRES_PASSWORD` | `studentpass` | db, api |
| `DB_HOST` | `db` | api |
| `DB_PORT` | `5432` | api |
| `API_PORT` | `5000` | api |
| `GRAFANA_ADMIN_USER` | `admin` | grafana |
| `GRAFANA_ADMIN_PASSWORD` | `admin` | grafana |

Rules: api reads config **only** from these env names (with the same fallbacks as `.env`), grafana admin creds come from env, no secrets in compose files.

## 4. API surface (A owns; B and C code against this)

Base URL inside network: `http://api:5000`. Healthcheck path: `/health`.

| Method | Path | Success | Notes |
|---|---|---|---|
| GET | `/health` | 200 `{"status":"ok","db":"ok"}` | must not touch metrics middleware |
| GET | `/students` | 200 `[...]` | list all |
| GET | `/students/<id>` | 200 `{...}` / 404 | |
| POST | `/students` | 201 `{...}` | body `{name,email,course}`; 400 on invalid, 409 on duplicate email |
| PUT | `/students/<id>` | 200 `{...}` / 404 | |
| DELETE | `/students/<id>` | 204 / 404 | |
| GET | `/metrics` | 200 text/plain | Prometheus exposition format |

JSON error shape everywhere: `{"error": "<message>"}`.

## 5. Database schema (A owns `db/init.sql`)

```sql
CREATE TABLE IF NOT EXISTS students (
  id         SERIAL PRIMARY KEY,
  name       TEXT NOT NULL,
  email      TEXT NOT NULL UNIQUE,
  course     TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- 5 seed rows, idempotent (`ON CONFLICT (email) DO NOTHING`).
- Mounted at `/docker-entrypoint-initdb.d/00-init.sql` (read-only). Runs **only** on an empty `pgdata` → always use `docker compose down -v` before a clean demo.
- API must retry DB connect (10 × 2s) before failing.

## 6. Metrics contract (A emits, B queries — frozen strings)

| Metric | Type | Labels | Required |
|---|---|---|---|
| `http_requests_total` | Counter | `method`, `route`, `status` | yes |
| `http_request_duration_seconds` | Histogram | `method`, `route` | yes |
| `http_requests_in_flight` | Gauge | — | optional |

- `route` is the **Flask route template** (`/students/<id>`), never the raw path (cardinality).
- Histogram buckets: `0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5`.
- `/health` and `/metrics` are excluded from `http_requests_total`.
- New metrics are **additive only**. Renaming anything in this table is a breaking change.
- Prod runs `gunicorn --workers 1` (single process = single metrics registry). Multi-worker requires prometheus multiprocess mode and is out of scope.

## 7. Prometheus config (B owns `monitoring/prometheus.yml`)

- `scrape_interval: 5s`, `evaluation_interval: 5s`
- Job `api` → `metrics_path: /metrics` → `targets: ['api:5000']`
- Mounted read-only at `/etc/prometheus/prometheus.yml`
- Must pass `promtool check config`.

## 8. Grafana provisioning (B owns, C mounts)

| Host path | Container path |
|---|---|
| `monitoring/grafana/provisioning/datasources/` | `/etc/grafana/provisioning/datasources` |
| `monitoring/grafana/provisioning/dashboards/` | `/etc/grafana/provisioning/dashboards` |
| `monitoring/grafana/dashboards/` | `/var/lib/grafana/dashboards` |

- Datasource: name `Prometheus`, uid `prometheus-ds`, type `prometheus`, url `http://prometheus:9090`, `isDefault: true`.
- Dashboard: uid `students-api`, title `Student API — Overview`, refresh `5s`, default range `now-15m`, JSON references uid `prometheus-ds` directly (no template variable).
- Zero manual clicking: a fresh `down -v` + `up` must show the dashboard.

**Required panels**

| Panel | Query |
|---|---|
| Request rate | `sum(rate(http_requests_total[1m]))` |
| p95 latency | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))` |
| Error rate (5xx %) | `100 * sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))` |
| Total requests | `sum(http_requests_total)` |
| Per-route rate | `sum by (route) (rate(http_requests_total[1m]))` |

## 9. Compose composition (C owns)

Base (`docker-compose.yml`): build/images, env, healthchecks, `app-net`, volumes, config mounts, **no host ports**.

| Overlay | Adds |
|---|---|
| `docker-compose.dev.yml` | bind-mount `./api:/app`, `FLASK_ENV=development` + `--reload`, publish `5000, 5432, 9090, 3000`, debug logging |
| `docker-compose.prod.yml` | removes bind mounts, `restart: unless-stopped`, resource limits, `gunicorn --workers 1`, publish only `5000, 3000` |

Merge semantics: maps merge per key, later `-f` wins; scalars replaced; `ports` appended. `docker compose config` is the proof artifact.

## 10. Healthchecks & startup order (C owns, A supplies `/health`)

| Service | Test | Interval / timeout / retries / start_period |
|---|---|---|
| `db` | `pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"` (double `$` = read container env, not host `.env`) | 5s / 3s / 10 / 10s |
| `api` | `python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://localhost:5000/health').status==200 else 1)"` | 10s / 3s / 5 / 15s |
| `prometheus` | `wget -qO- http://localhost:9090/-/healthy` | 10s / 3s / 5 / 10s |
| `grafana` | `wget -qO- http://localhost:3000/api/health` | 10s / 3s / 5 / 10s |

Dependencies: `api → db (service_healthy)`; `prometheus → api (service_started)`; `grafana → prometheus (service_started)`. Never `service_healthy` on prometheus/grafana (deadlock risk).

## 11. Repository layout & ownership (do not edit another member's files)

```
.
├── .env.example                         C
├── .gitignore                           C
├── docker-compose.yml                   C
├── docker-compose.dev.yml               C
├── docker-compose.prod.yml              C
├── Makefile                             C
├── README.md                            C
├── docs/CONTRACT.md                     all (frozen)
├── docs/DEMO.md                         C
├── docs/NOTES.md                        all (append-only)
├── api/Dockerfile, requirements.txt, app.py, db.py   A
├── db/init.sql                          A
├── monitoring/prometheus.yml            B
├── monitoring/grafana/provisioning/...  B
├── monitoring/grafana/dashboards/students-api.json  B
└── scripts/traffic.sh                   C
```

## 12. Commands (C owns the entry points; everyone uses these names)

```
make dev      # docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
make prod     # docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
make down     # down (keeps volumes)
make clean    # down -v (wipes volumes — required before clean demo)
make traffic  # runs scripts/traffic.sh against localhost:5000
make config   # docker compose config (merged output)
```

## 13. Conventions

- All timestamps UTC (`timestamptz`).
- `.sh` files: LF line endings, `set -euo pipefail`.
- Python: `requirements.txt` pinned (`flask`, `psycopg2-binary`, `prometheus-client`, `gunicorn`).
- No secrets or `.env` committed. `.gitignore`: `.env`, `__pycache__/`, `*.pyc`, `.DS_Store`.
- Branch per member; C merges to `main` at G1 and G2.

## 14. Gates (binary pass/fail)

**G0 (T+1:00)** — contract frozen; `docker compose config` valid on all three files.
**G1 (T+2:45)** — `make dev` → 4 containers up, `api`/`db` healthy, `GET /students` returns seed rows, Prometheus target `api` = UP, Grafana datasource reachable in Explore.
**G2 (T+5:00)** — after `make clean`, both `make dev` and `make prod` reach all-healthy; dashboard auto-loads with populated panels; prod exposes only 5000/3000.

## 15. Change control

1. Append to `docs/NOTES.md`: what changed, why, who agreed.
2. Additive changes (new endpoint, new metric, new panel) need one other member's sign-off.
3. Renames of any service name, port, env key, metric name/label, mount path, or container path: all three must agree, then update this file in the same commit.
