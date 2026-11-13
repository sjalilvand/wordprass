# ============================================================
#  WordPress Clone Agent - Windows launcher (PowerShell)
#  Ejent-e klon-e WordPress | https://github.com/sjalilvand/wordprass
#
#  Usage:
#    powershell -ExecutionPolicy Bypass -File run.ps1
#    (or just run run.bat)
# ============================================================
param([int]$Port = 8765)

$ErrorActionPreference = "Stop"

function Write-Banner {
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host "   WordPress Clone Agent  -  Web Panel        " -ForegroundColor Cyan
    Write-Host "   github.com/sjalilvand/wordprass            " -ForegroundColor DarkCyan
    Write-Host "==============================================" -ForegroundColor Cyan
}

function Find-Python {
    foreach ($cmd in @("py", "python", "python3")) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) {
            # reject the WindowsApps store stub that just opens Microsoft Store
            $src = $found.Source
            if ($src -and $src -like "*WindowsApps*python*.exe*" -and $cmd -eq "python") {
                continue
            }
            return $cmd
        }
    }
    return $null
}

function Refresh-Path {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

Write-Banner

# ---------- 1) find python ----------
$py = Find-Python
if (-not $py) {
    Write-Host "[!] Python not found on this PC." -ForegroundColor Yellow
    Write-Host "    Python dar in computer peyda nashod." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "[..] Installing Python 3.12 with winget (a few minutes)..." -ForegroundColor Cyan
        try {
            winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
        } catch {
            Write-Host "[!] winget install failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
        Refresh-Path
        $py = Find-Python
    }
    if (-not $py) {
        Write-Host "[X] Please install Python from: https://www.python.org/downloads/" -ForegroundColor Red
        Write-Host "    (Dar hengame nasb, gozine-ye 'Add Python to PATH' ra fa'al konid)" -ForegroundColor Red
        Write-Host "    Then run this script again." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Host "[OK] Python found: $py" -ForegroundColor Green

# ---------- 2) virtual environment ----------
$venvDir = Join-Path $PSScriptRoot ".venv"
$pyExe   = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $pyExe)) {
    Write-Host "[..] Creating virtual environment (.venv)..." -ForegroundColor Cyan
    & $py -m venv $venvDir
    if (-not (Test-Path $pyExe)) {
        Write-Host "[X] Could not create venv; using system Python instead." -ForegroundColor Yellow
        $pyExe = $py
    }
}

# ---------- 3) requirements ----------
Write-Host "[..] Checking requirements (first run downloads packages)..." -ForegroundColor Cyan
& $pyExe -m pip install --quiet --disable-pip-version-check --upgrade pip
& $pyExe -m pip install --quiet --disable-pip-version-check -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] pip install failed. Check your internet connection." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Requirements ready." -ForegroundColor Green

# ---------- 4) run web panel ----------
Write-Host ""
Write-Host "[OK] Starting web panel..." -ForegroundColor Green
Write-Host "     URL: http://127.0.0.1:$Port" -ForegroundColor White
Write-Host "     The browser will open automatically." -ForegroundColor White
Write-Host "     Baraye payan: Ctrl+C" -ForegroundColor DarkGray
Write-Host ""

& $pyExe (Join-Path $PSScriptRoot "wp_clone_agent.py") --webui --port $Port
