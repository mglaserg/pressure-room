@echo off
setlocal
cd /d "%~dp0"

echo Starting Pressure Room API...
start "Pressure Room API" cmd /k "cd /d ""%~dp0backend"" && uv sync && uv run uvicorn app.main:app --reload --port 8000"

echo Starting Pressure Room web app...
start "Pressure Room Web" cmd /k "cd /d ""%~dp0frontend"" && npm install && npm run dev"

timeout /t 5 /nobreak >nul
start http://localhost:3000
endlocal
