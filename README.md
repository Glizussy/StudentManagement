# Student API + Monitoring Stack

Multi-container deployment with Docker Compose: a Flask Student API, PostgreSQL,
Prometheus, and a Grafana dashboard provisioned entirely from files.

## Architecture

```
browser :3000 ──► grafana ──query──► prometheus:9090
                                        │ scrape :5000/metrics every 5s
traffic :5001 ──► api ──psycopg2──► db:5432
                    └── counters/histograms (prometheus_client)
```

- One bridge network, `app-net`; containers resolve each other by **service name**.
- Named volumes `pgdata`, `prom-data`, `grafana-data` persist state.
- Config is mounted, never baked in: `prometheus.yml`, `init.sql`, Grafana provisioning.

## Quick start

```
cp .env.example .env            # PowerShell: Copy-Item .env.example .env
make clean                      # start from an empty data volume
make dev                        # four containers healthy in roughly 20 seconds
make traffic                    # 30s baseline plus a 10s spike
```

- API: http://localhost:5001/students and `/metrics`
- Prometheus: http://localhost:9090 (dev only)
- Grafana: http://localhost:3000 (`admin` / `admin`), dashboard "Student API - Overview"

Verify the deployment with the acceptance script:

```
.\scripts\acceptance.ps1 -RequireTraffic
```

## Compose matrix

| File | Purpose | Publishes |
|---|---|---|
| `docker-compose.yml` | base: services, network, volumes, healthchecks, config mounts | nothing |
| `docker-compose.dev.yml` | bind-mounted source, Flask `--reload`, debug logging | 5001, 5432, 9090, 3000 |
| `docker-compose.prod.yml` | gunicorn `-w 1`, restart policies, resource limits | 5001, 3000 |

The API listens on **5000 inside the container**; the host mapping is `5001:5000` because TCP 5000
is in a Windows excluded port range on the demo machine. Scrape target and healthcheck are unaffected.

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

Gate checks (G1/G2, and demo pre-flight):

```
.\scripts\acceptance.ps1                     # stack, health, target, dashboard, prod ports
.\scripts\acceptance.ps1 -RequireTraffic     # also assert metrics arrived
```

## Verification

Observed on a clean volume in both environments:

| Check | Result |
|---|---|
| Containers healthy | 4 of 4, cold start about 22s including build |
| Seeded records | 5 students from `init.sql` |
| Prometheus target | `api` UP at `http://api:5000/metrics` |
| Grafana provisioning | dashboard auto-loaded, 5 panels, no manual import |
| Traffic (400 requests) | rate about 7 req/s, p95 about 29 ms, total counter 400+ |
| Error-rate panel | reads 0 without 5xx responses |
| Prod exposure | only 5001 and 3000 published; `db` and `prometheus` internal |
| `acceptance.ps1 -RequireTraffic` | 7 of 7 checks pass |

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
scripts/acceptance.ps1                      gate checks (health, target, dashboard, prod ports)
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
| Target `api` DOWN | scrape config or API not exposing `/metrics` | check `monitoring/prometheus.yml`, `curl localhost:5001/metrics` |
| Dashboard has no panels | provisioning path wrong | mount must be `/etc/grafana/provisioning` |
| Tables missing | `init.sql` only runs on empty `pgdata` | `make clean` then `make dev` |
| `api` won't start: "ports are not available" | TCP 5000 reserved by Windows | see excluded ranges: `netsh interface ipv4 show excludedportrange protocol=tcp`; we map `5001:5000` |
| `db` logs "Is a directory" | `db/init.sql` did not exist at first `up` | file exists in the repo, then `make clean` |
| Panels show "No data" | metric names or labels differ | compare with CONTRACT section 6 |
| Error-rate panel blank | no 5xx series yet | query ends in `or vector(0)`, so it reads 0 |
