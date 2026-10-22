# ---------- LiveKit Agent Worker ----------
# Build: docker build -t voiceagent-worker .
# Run:   docker run --env-file .env voiceagent-worker
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required by some native wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY voiceagent/ voiceagent/

# Download Silero VAD model at build time so cold-starts are fast
RUN python -m voiceagent.main download-files || true

# Run the agent worker in production mode
CMD ["python", "-m", "voiceagent.main", "start"]
