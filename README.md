# Student API + Monitoring Stack

Multi-container deployment with Docker Compose: a Flask Student API, PostgreSQL,
Prometheus, and a Grafana dashboard provisioned entirely from files.

## Architecture

```
browser :3000 ──► grafana ──query──► prometheus:9090
                                        │ scrape :5000/metrics every 5s
traffic :5000 ──► api ──psycopg2──► db:5432
                    └── counters/histograms (prometheus_client)
```

- One bridge network, `app-net`; containers resolve each other by **service name**.
- Named volumes `pgdata`, `prom-data`, `grafana-data` persist state.
- Config is mounted, never baked in: `prometheus.yml`, `init.sql`, Grafana provisioning.

## Quick start

```
cp .env.example .env
make dev          # dev overlay: hot reload, DB + Prometheus + Grafana exposed
make traffic      # ~40s of GET/POST traffic with a visible spike
```

- API: http://localhost:5000/students and `/metrics`
- Prometheus: http://localhost:9090 (dev only)
- Grafana: http://localhost:3000 (`admin` / `admin`), dashboard "Student API - Overview"

## Compose matrix

| File | Purpose | Publishes |
|---|---|---|
| `docker-compose.yml` | base: services, network, volumes, healthchecks, config mounts | nothing |
| `docker-compose.dev.yml` | bind-mounted source, Flask `--reload`, debug logging | 5000, 5432, 9090, 3000 |
| `docker-compose.prod.yml` | gunicorn `-w 1`, restart policies, resource limits | 5000, 3000 |

Compose merges later files over earlier ones: maps merge per key, scalars are replaced,
`ports` are appended. Inspect the merged result with `make config`.

Always `make down` before switching overlays.

## Commands

| Command | Action |
|---|---|
| `make dev` | base + dev overlay, build and start detached |
| `make prod` | base + prod overlay, build and start detached |
| `make down` | stop and remove containers, keep volumes |
| `make clean` | `down -v`, wipes data (required before a clean demo) |
| `make traffic` | run `scripts/traffic.sh` |
| `make config` | print the merged dev configuration |

On Windows without `make`, the PowerShell wrapper exposes the same targets:

```
.\scripts\stack.ps1 dev
.\scripts\stack.ps1 prod
.\scripts\stack.ps1 down
.\scripts\stack.ps1 clean
.\scripts\stack.ps1 traffic
.\scripts\stack.ps1 config
```

## Services

| Service | Image | Health | Notes |
|---|---|---|---|
| `api` | `build ./api` | `python` probe on `/health` | depends on `db` healthy |
| `db` | `postgres:16.4-alpine` | `pg_isready` | schema from `db/init.sql`, runs on empty volume |
| `prometheus` | `prom/prometheus:v2.53.0` | `/-/healthy` | scrapes `api:5000/metrics` |
| `grafana` | `grafana/grafana:11.1.0` | `/api/health` | dashboards from mounted provisioning |

## Three concepts demonstrated

1. **Config file mounts** - `prometheus.yml`, `init.sql`, and Grafana provisioning are
   bind-mounted read-only. No `docker cp`, no manual import.
2. **Service discovery by name** - `DB_HOST=db`, datasource `http://prometheus:9090`,
   scrape target `api:5000`. No IPs.
3. **Multiple `-f` files** - one base plus dev/prod deltas instead of duplicated stacks.

## Repository layout

```
docker-compose.yml / .dev.yml / .prod.yml   orchestration
Makefile                                    entry points
.env.example                                required keys
scripts/traffic.sh / traffic.ps1           demo load generator (bash / PowerShell)
scripts/stack.ps1                           PowerShell mirror of the Makefile targets
docs/CONTRACT.md                            frozen shared contract
docs/DEMO.md                                timed demo runbook
docs/NOTES.md                               issue log
api/                                        Member A: Flask app + Dockerfile
db/init.sql                                 Member A: schema + seed
monitoring/                                 Member B: Prometheus config, Grafana provisioning
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `api` unhealthy | DB not ready / bad credentials | `docker compose logs api`, check `.env` |
| Target `api` DOWN | scrape config or API not exposing `/metrics` | check `monitoring/prometheus.yml`, `curl localhost:5000/metrics` |
| Dashboard has no panels | provisioning path wrong | mount must be `/etc/grafana/provisioning` |
| Tables missing | `init.sql` only runs on empty `pgdata` | `make clean` then `make dev` |
| Panels show "No data" | metric names or labels differ | compare with CONTRACT section 6 |
