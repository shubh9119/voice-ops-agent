#!/usr/bin/env bash
set -e

if [ "$1" = "docker" ]; then
    echo "Starting with Docker Compose..."
    docker compose up --build
    exit 0
fi

echo "Starting Omnibound Brand Q&A Agent..."

# Run backend in background
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Run frontend
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Backend running on http://localhost:8000 (PID: $BACKEND_PID)"
echo "Frontend running on http://localhost:3000 (PID: $FRONTEND_PID)"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
