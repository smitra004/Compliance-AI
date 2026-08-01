@echo off
title ComplianceAI — Start All Services
echo.
echo ╔══════════════════════════════════════════╗
echo ║   ComplianceAI — Starting Services...    ║
echo ╚══════════════════════════════════════════╝
echo.

:: Start FastAPI backend in a new window
:: NOTE: port 8010 is used instead of 8000 because Windows blocks 8000 on
:: some machines (WinError 10013 - excluded port range / Hyper-V reservation).
:: If 8010 is also blocked for you, run "netsh int ipv4 show excludedportrange tcp"
:: to see blocked ranges and pick a free port, updating this file and
:: frontend/vite.config.js to match.
echo [1/2] Starting FastAPI backend on http://127.0.0.1:8010 ...
start "ComplianceAI Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload"

:: Wait a moment for the backend to initialize
timeout /t 3 /nobreak >nul

:: Start Vite frontend dev server in a new window
echo [2/2] Starting Vite frontend on http://localhost:5173 ...
start "ComplianceAI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ✓ Both servers are starting.
echo   Backend:  http://127.0.0.1:8010
echo   Frontend: http://localhost:5173
echo.
echo Press any key to close this launcher...
pause >nul
