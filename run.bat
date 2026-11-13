@echo off
rem WordPress Clone Agent - easy launcher (double-click me)
rem PowerShell execution policy is bypassed here automatically
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
echo.
pause
