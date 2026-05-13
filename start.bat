@echo off
echo ========================================
echo   SJM-Werewolf - Starting servers...
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Starting backend (FastAPI :8765)...
start "Werewolf-Backend" cmd /c "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8765 --reload"

echo [2/2] Starting frontend (Vite :5173)...
start "Werewolf-Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo ========================================
echo   Backend:  http://localhost:8765
echo   Frontend: http://localhost:5173
echo ========================================
echo.
echo Close this window or press any key to exit.
pause >nul
