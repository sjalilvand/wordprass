@echo off
rem ============================================
rem  Dynamic site - easy launcher (double-click)
rem ============================================
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe app.py
    goto :end
)
where py >nul 2>nul && (py -m pip install -r requirements.txt && py app.py && goto :end)
where python >nul 2>nul && (python -m pip install -r requirements.txt && python app.py && goto :end)
echo [!] Python not found. Install from https://www.python.org/downloads/
pause
:end
pause
