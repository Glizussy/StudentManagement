# Build notes

Append-only log. One entry per issue: symptom, root cause, fix, owner.

## Template

```
### <timestamp UTC> - <symptom>
- Root cause:
- Fix:
- Owner:
- Gate:
```

## Entries

### 2026-10-27 - repo scaffolded (Member C)
- Root cause: n/a
- Fix: base compose + dev/prod overlays + Makefile + traffic script + docs
- Owner: C
- Gate: G0 (pending `docker compose config` run with api/ and monitoring/ present)

### 2026-10-27 - api container failed: "ports are not available ... forbidden"
- Root cause: TCP 5000 is in a Windows excluded port range
  (`netsh interface ipv4 show excludedportrange protocol=tcp` lists 5000-5000).
  Docker could not bind the host port.
- Fix: host mapping changed to `5001:5000` in both overlays, traffic scripts, README, DEMO and
  CONTRACT. Container port, `API_PORT`, healthcheck URL and scrape target stay 5000.
- Owner: C
- Gate: G1

### 2026-10-27 - db exited: "could not read from input file: Is a directory"
- Root cause: bind-mounting `./db/init.sql` before the file exists makes Docker create a
  *directory* at that path, and Postgres then fails reading the init script.
- Fix: `db/init.sql` must exist before the first `up`; documented in README troubleshooting.
- Owner: A (file) / C (doc)
- Gate: G1

### 2026-10-27 - `make` is not installed on the Windows demo machine
- Root cause: Git for Windows / Docker Desktop do not ship GNU make
- Fix: added `scripts/stack.ps1` (same targets as the Makefile) and `scripts/traffic.ps1`;
  Makefile remains the canonical entry point and is documented first
- Owner: C
- Gate: G0
