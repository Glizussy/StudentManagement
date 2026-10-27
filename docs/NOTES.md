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

### 2026-10-27 - `make` is not installed on the Windows demo machine
- Root cause: Git for Windows / Docker Desktop do not ship GNU make
- Fix: added `scripts/stack.ps1` (same targets as the Makefile) and `scripts/traffic.ps1`;
  Makefile remains the canonical entry point and is documented first
- Owner: C
- Gate: G0
