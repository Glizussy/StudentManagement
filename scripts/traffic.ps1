param(
    [string]$BaseUrl = "http://localhost:5000",
    [int]$BaselineSeconds = 30,
    [int]$SpikeSeconds = 10,
    [int]$BaselineRps = 5,
    [int]$SpikeRps = 25
)

$ErrorActionPreference = "Stop"

function Send-Post {
    param([int]$i)

    $email = "demo-$([guid]::NewGuid().ToString('N'))-$i@example.com"
    $body = @{
        name   = "Load Test $i"
        email  = $email
        course = "Demo"
    } | ConvertTo-Json -Compress

    & curl.exe -s -o NUL --max-time 5 -X POST "$BaseUrl/students" `
        -H "Content-Type: application/json" -d $body | Out-Null
}

function Send-Hit {
    param([int]$i)

    switch ($i % 10) {
        0 { & curl.exe -s -o NUL --max-time 5 "$BaseUrl/students/999999" | Out-Null }
        1 { Send-Post -i $i }
        2 { Send-Post -i $i }
        default { & curl.exe -s -o NUL --max-time 5 "$BaseUrl/students" | Out-Null }
    }
}

Write-Host "=== BASELINE: ${BaselineSeconds}s at ~${BaselineRps} req/s ==="
for ($s = 0; $s -lt $BaselineSeconds; $s++) {
    for ($i = 1; $i -le $BaselineRps; $i++) {
        Send-Hit -i $i
    }
    Start-Sleep -Seconds 1
}

Write-Host "=== SPIKE: ${SpikeSeconds}s at ~${SpikeRps} req/s ==="
for ($s = 0; $s -lt $SpikeSeconds; $s++) {
    for ($i = 1; $i -le $SpikeRps; $i++) {
        Send-Hit -i $i
    }
    Start-Sleep -Seconds 1
}

$total = ($BaselineSeconds * $BaselineRps) + ($SpikeSeconds * $SpikeRps)
Write-Host "=== DONE: ~$total requests sent ==="
