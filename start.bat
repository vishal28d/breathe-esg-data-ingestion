@echo off
REM =============================================================================
REM start.bat — Breathe ESG Dev Startup Script (Windows native)
REM
REM Starts the Django backend and React frontend in separate console windows.
REM   Backend:  http://localhost:8000
REM   Frontend: http://localhost:5173
REM   Admin:    http://localhost:8000/admin  (admin / admin)
REM
REM Usage: double-click start.bat  OR  run it in a terminal
REM =============================================================================

SETLOCAL ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo.
echo [breathe-esg] Checking Python venv...
IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [WARN] venv not found — creating one now...
    python -m venv venv
    IF ERRORLEVEL 1 (
        echo [ERROR] Could not create venv. Is Python installed?
        pause
        exit /b 1
    )
    echo [OK] venv created.
)

REM Activate venv
call venv\Scripts\activate.bat
echo [OK] Python venv activated.

REM ---------------------------------------------------------------------------
REM Install Python deps
REM ---------------------------------------------------------------------------
IF EXIST "requirements.txt" (
    echo [breathe-esg] Installing Python dependencies...
    pip install -q -r requirements.txt
    echo [OK] Python deps ready.
) ELSE (
    echo [WARN] requirements.txt not found — skipping pip install.
)

REM ---------------------------------------------------------------------------
REM Run Django migrations
REM ---------------------------------------------------------------------------
echo [breathe-esg] Running Django migrations...
python manage.py migrate --run-syncdb
echo [OK] Migrations applied.

REM ---------------------------------------------------------------------------
REM Load fixtures (errors are non-fatal — may already be loaded)
REM ---------------------------------------------------------------------------
echo [breathe-esg] Loading initial fixtures...
python manage.py loaddata api/fixtures/initial_data.json 2>nul
echo [OK] Fixtures loaded (or already present).

REM ---------------------------------------------------------------------------
REM Check frontend node_modules
REM ---------------------------------------------------------------------------
IF NOT EXIST "frontend\node_modules" (
    echo [breathe-esg] node_modules not found — running npm install...
    cd frontend
    npm install
    cd ..
    echo [OK] Frontend deps installed.
)

REM ---------------------------------------------------------------------------
REM Start backend in a new window
REM ---------------------------------------------------------------------------
echo [breathe-esg] Starting Django backend on http://localhost:8000 ...
start "Breathe ESG — Backend" cmd /k "call venv\Scripts\activate.bat && python manage.py runserver 8000"

REM ---------------------------------------------------------------------------
REM Start frontend in a new window
REM ---------------------------------------------------------------------------
echo [breathe-esg] Starting React frontend on http://localhost:5173 ...
start "Breathe ESG — Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo   Breathe ESG is running!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   Admin:    http://localhost:8000/admin
echo             (user: admin / pass: admin)
echo   Close the two terminal windows to stop
echo ========================================
echo.

ENDLOCAL
