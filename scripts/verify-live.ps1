$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Install the local environment first: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt'
}

$prompted = -not [bool]$env:NEBIUS_API_KEY
try {
    if ($prompted) {
        $secureKey = Read-Host 'Nebius Token Factory API key (input hidden)' -AsSecureString
        $credential = [pscredential]::new('nebius', $secureKey)
        $env:NEBIUS_API_KEY = $credential.GetNetworkCredential().Password
    }
    Push-Location -LiteralPath $projectRoot
    try {
        & $python -m scripts.verify_live
        if ($LASTEXITCODE -ne 0) { throw "Live verification failed (exit $LASTEXITCODE)." }
    } finally {
        Pop-Location
    }
} finally {
    if ($prompted) { Remove-Item Env:NEBIUS_API_KEY -ErrorAction SilentlyContinue }
    $credential = $null
    $secureKey = $null
}
