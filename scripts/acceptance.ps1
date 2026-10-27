param(
    [string]$ApiBase = "http://localhost:5001",
    [string]$Prometheus = "http://localhost:9090",
    [string]$Grafana = "http://localhost:3000",
    [string]$GrafanaUser = "admin",
    [string]$GrafanaPassword = "admin",
    [int]$WaitSeconds = 120,
    [switch]$RequireTraffic
)

$ErrorActionPreference = "Stop"
$failures = 0

function Check {
    param([string]$Name, [scriptblock]$Test)

    try {
        $detail = & $Test
        Write-Host ("PASS  {0,-34} {1}" -f $Name, $detail)
    }
    catch {
        Write-Host ("FAIL  {0,-34} {1}" -f $Name, $_.Exception.Message)
        $script:failures++
    }
}

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root

try {
    $deadline = (Get-Date).AddSeconds($WaitSeconds)
    $healthy = 0
    while ((Get-Date) -lt $deadline) {
        $states = @(docker compose ps --format json 2>$null | ForEach-Object { $_ | ConvertFrom-Json })
        $healthy = @($states | Where-Object { $_.Health -eq "healthy" }).Count
        if ($healthy -eq 4) {
            break
        }
        Write-Host "waiting for containers to become healthy ($healthy of 4)..."
        Start-Sleep -Seconds 2
    }

    Check "containers healthy (4)" {
        $states = @(docker compose ps --format json | ForEach-Object { $_ | ConvertFrom-Json })
        if ($states.Count -ne 4) {
            throw "expected 4 services, found $($states.Count)"
        }
        $unhealthy = @($states | Where-Object { $_.Health -ne "healthy" })
        if ($unhealthy.Count -gt 0) {
            throw "not healthy: " + (($unhealthy | ForEach-Object { $_.Service }) -join ", ")
        }
        "all 4 healthy"
    }

    Check "api /health" {
        $r = Invoke-RestMethod -Uri "$ApiBase/health" -TimeoutSec 5
        if ($r.status -ne "ok" -or $r.db -ne "ok") {
            throw "unexpected body: $($r | ConvertTo-Json -Compress)"
        }
        "status ok, db ok"
    }

    Check "api /students has rows" {
        $rows = Invoke-RestMethod -Uri "$ApiBase/students" -TimeoutSec 5
        $count = ($rows | Measure-Object).Count
        if ($count -lt 1) {
            throw "student list is empty (did init.sql run on an empty volume?)"
        }
        "$count rows"
    }

    Check "prometheus target api UP" {
        $t = Invoke-RestMethod -Uri "$Prometheus/api/v1/targets" -TimeoutSec 5
        $api = @($t.data.activeTargets | Where-Object { $_.labels.job -eq "api" })
        if ($api.Count -eq 0) {
            throw "job 'api' not found"
        }
        if ($api[0].health -ne "up") {
            throw "target is $($api[0].health): $($api[0].lastError)"
        }
        $api[0].scrapeUrl
    }

    Check "grafana dashboard provisioned" {
        $token = [Convert]::ToBase64String(
            [Text.Encoding]::UTF8.GetBytes("${GrafanaUser}:${GrafanaPassword}")
        )
        $d = Invoke-RestMethod -Uri "$Grafana/api/dashboards/uid/students-api" `
            -Headers @{ Authorization = "Basic $token" } -TimeoutSec 5
        $panels = @($d.dashboard.panels).Count
        if ($panels -lt 5) {
            throw "dashboard '$($d.dashboard.title)' has $panels panels, contract requires 5"
        }
        "$($d.dashboard.title), $panels panels"
    }

    Check "prod publishes only 5001/3000" {
        $cfg = docker compose -f docker-compose.yml -f docker-compose.prod.yml config
        $published = @(
            ($cfg | Select-String -Pattern 'published: "(\d+)"' -AllMatches).Matches |
                ForEach-Object { $_.Groups[1].Value }
        )
        $bad = @($published | Where-Object { $_ -notin @("5001", "3000") })
        if ($bad.Count -gt 0) {
            throw "unexpected published ports: $($bad -join ", ")"
        }
        "5001, 3000"
    }

    if ($RequireTraffic) {
        Check "http_requests_total has series" {
            $q = Invoke-RestMethod -Uri "$Prometheus/api/v1/query?query=sum(http_requests_total)" -TimeoutSec 5
            if (@($q.data.result).Count -eq 0) {
                throw "no series yet, run the traffic script first"
            }
            "current total = $($q.data.result[0].value[1])"
        }
    }
}
finally {
    Pop-Location
}

if ($failures -gt 0) {
    Write-Host ""
    Write-Host "$failures check(s) FAILED"
    exit 1
}

Write-Host ""
Write-Host "All checks passed"
