@echo off
echo ========================================================
echo   Starting Omnibound Brand Q^&A Agent (Backend + Frontend)
echo ========================================================

REM Check if docker is requested
if "%1"=="docker" (
    echo Starting with Docker Compose...
    docker compose up --build
    exit /b
)

echo Starting Backend on http://localhost:8000...
start "Omnibound Backend" cmd /k "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Frontend on http://localhost:3000...
start "Omnibound Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Services launched!
echo - Backend API:  http://localhost:8000
echo - Swagger Docs: http://localhost:8000/docs
echo - Frontend UI:  http://localhost:3000
echo.
