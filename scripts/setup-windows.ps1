$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host 'Setting up PARALLAX Studio...' -ForegroundColor Green
if (-not (Test-Path '.venv')) { py -3.12 -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if (-not (Test-Path '.env')) {
  Copy-Item '.env.example' '.env'
  Write-Host 'Created .env. Add your NEBIUS_API_KEY to enable real model inference.' -ForegroundColor Yellow
}
Write-Host 'Start: .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000' -ForegroundColor Cyan
Write-Host 'Then visit http://127.0.0.1:8000'
