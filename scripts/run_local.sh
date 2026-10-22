#!/usr/bin/env bash
set -e

# =======================================================================
# VoiceOps - Local Development Startup Script (Unix/macOS/WSL)
# =======================================================================

echo "======================================================================="
echo "          VoiceOps - Operator-Guided Voice AI Agent Launcher           "
echo "======================================================================="

if [ ! -f .env ]; then
    echo "[INFO] Creating .env from .env.example..."
    cp .env.example .env
    echo "[ACTION REQUIRED] Please edit .env with your DEEPGRAM_API_KEY and GROQ_API_KEY."
fi

echo "Choose startup mode:"
echo "  [1] Docker Compose (Recommended: Full Stack including LiveKit SFU)"
echo "  [2] Seed demo call and start Backend + Frontend locally"
echo "  [3] Run unit test suites (Backend + Compliance + Latency)"
read -p "Enter choice (1-3): " MODE

case "$MODE" in
    1)
        echo "Starting Docker Compose..."
        docker compose up --build
        ;;
    2)
        echo "Seeding demo call..."
        python3 scripts/seed_demo_call.py
        echo "Starting FastAPI backend..."
        (cd backend && uvicorn app.main:app --reload --port 8000) &
        echo "Starting Next.js frontend..."
        (cd web && npm run dev) &
        wait
        ;;
    3)
        echo "Running test suites..."
        python3 -m pytest backend/tests -v
        python3 -m pytest agent/tests -v
        ;;
    *)
        echo "Invalid option."
        exit 1
        ;;
esac
