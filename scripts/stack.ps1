param(
    [Parameter(Position = 0)]
    [ValidateSet("dev", "prod", "down", "clean", "traffic", "config")]
    [string]$Action = "dev"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root

try {
    switch ($Action) {
        "dev" {
            docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
        }
        "prod" {
            docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
        }
        "down" {
            docker compose down
        }
        "clean" {
            docker compose down -v
        }
        "traffic" {
            & "$PSScriptRoot\traffic.ps1"
        }
        "config" {
            docker compose -f docker-compose.yml -f docker-compose.dev.yml config
        }
    }

    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
