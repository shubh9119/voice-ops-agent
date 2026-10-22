@echo off
REM =======================================================================
REM VoiceOps - Local Development Startup Script
REM =======================================================================

echo.
echo =======================================================================
echo           VoiceOps - Operator-Guided Voice AI Agent Launcher
echo =======================================================================
echo.

if not exist .env (
    echo [INFO] Creating .env from .env.example...
    copy .env.example .env
    echo [ACTION REQUIRED] Please edit .env with your DEEPGRAM_API_KEY and GROQ_API_KEY.
)

echo Choose startup mode:
echo   [1] Docker Compose (Recommended: Full Stack including LiveKit SFU)
echo   [2] Seed realistic demo call and start Backend + Frontend locally
echo   [3] Run unit test suites (Backend + Compliance + Latency)
echo.
set /p MODE="Enter choice (1-3): "

if "%MODE%"=="1" (
    echo Starting Docker Compose...
    docker compose up --build
    goto end
)

if "%MODE%"=="2" (
    echo Seeding realistic demo call into database...
    python scripts\seed_demo_call.py
    echo.
    echo Starting FastAPI backend in a new window...
    start "VoiceOps Backend" cmd /k "cd backend && uvicorn app.main:app --reload --port 8000"
    echo.
    echo Starting Next.js frontend in a new window...
    start "VoiceOps Frontend" cmd /k "cd web && npm run dev"
    echo.
    echo [DONE] Backend at http://localhost:8000, Frontend at http://localhost:3000
    goto end
)

if "%MODE%"=="3" (
    echo Running Backend & Compliance Tests...
    python -m pytest backend\tests -v
    echo.
    echo Running Latency Computation Tests...
    python -m pytest agent\tests -v
    goto end
)

:end
echo.
pause
