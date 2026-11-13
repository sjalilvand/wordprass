# Launcher for the generated dynamic site (PowerShell)
param([int]$Port = 8766)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$pyExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pyExe)) {
    $py = $null
    foreach ($cmd in @("py", "python", "python3")) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) { $py = $cmd; break }
    }
    if (-not $py) {
        Write-Host "[X] Python not found. Install from https://www.python.org/downloads/" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[..] Creating virtual environment..." -ForegroundColor Cyan
    & $py -m venv (Join-Path $PSScriptRoot ".venv")
    & $pyExe -m pip install --quiet --disable-pip-version-check -r (Join-Path $PSScriptRoot "requirements.txt")
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  Dynamic site  ->  http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "  Admin panel  ->  http://127.0.0.1:$Port/admin" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
$env:PORT = "$Port"
& $pyExe app.py
