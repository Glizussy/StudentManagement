# Demo runbook

Target: under 5 minutes, no typing beyond the listed commands.
Run everything from the repo root in Git Bash, WSL, or PowerShell.

If `make` is not installed, use the PowerShell wrapper with the same target names:
`.\scripts\stack.ps1 dev`, `stack.ps1 traffic`, `stack.ps1 down`, `stack.ps1 clean`, `stack.ps1 config`.

## Pre-flight (T-30 min)

```
docker compose version          # must be v2
docker compose build            # pre-build; never compile during the demo
make clean                      # wipe volumes so init.sql runs
```

- Terminal font size up; close Slack and notifications.
- Backup: dashboard screenshot + 60s screen recording of the live update.
- Fallback: `make config` output to prove the overlay merge if Docker won't start.

## Step 1 - cold start (0:00, ~60-90s)

```
make dev
docker compose ps
```

Expected: `api` and `db` **healthy**, `prometheus` and `grafana` **healthy** or starting.
Say: "Four services, one network, names resolved by Docker DNS; no hardcoded IPs."

## Step 2 - service discovery (1:30, 20s)

```
docker compose exec api python -c "import socket;print(socket.gethostbyname('db'))"
curl -s localhost:5000/health
curl -s localhost:5000/students
```

Expected: a container IP, `{"status":"ok","db":"ok"}`, and the 5 seed students
(proves `init.sql` ran via the config mount).

## Step 3 - metrics (1:50, 20s)

```
curl -s localhost:5000/metrics | grep http_requests_total | head
```

Say: "The API exports counters and a latency histogram; Prometheus pulls them every 5s."

## Step 4 - live dashboard (2:10, 15s)

Open http://localhost:3000, log in as `admin` / `admin`.
Expected: dashboard **already provisioned**, datasource already selected, refresh 5s.
Say: "Datasource and dashboard come from mounted provisioning files - zero manual setup."

## Step 5 - traffic (2:30, 45s)

```
make traffic
```

Expected: 30s baseline at ~5 req/s, then 10s spike at ~25 req/s.
In Grafana: request rate steps up, p95 rises, per-route panel splits.

## Step 6 - override files (3:30, 30s)

```
make down
docker compose -f docker-compose.yml -f docker-compose.prod.yml config ^
  | grep -E "restart:|published" | head
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Say: "Same base file; prod overlay adds restart policies and limits, and publishes only
5000 and 3000 - the database and Prometheus stay internal."

## Step 7 - close (4:00)

Restart dev for Q&A: `make dev`

## Failure fallback

| Symptom | Say | Do |
|---|---|---|
| api unhealthy | "DB handshake timing" | `docker compose logs api` |
| Dashboard empty | "scrape interval is 5s" | wait 15s, check Prometheus targets |
| Grafana won't start | "cold image pull" | switch to screenshot/video |
| Docker daemon down | "here's the recorded run" | play the 60s recording |
