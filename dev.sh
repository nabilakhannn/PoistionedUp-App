#!/bin/bash
# Start both frontend and backend dev servers.
# Usage: ./dev.sh
# Stop:  Ctrl+C (kills both)

trap 'kill 0' EXIT

echo "Starting FastAPI backend on :8000..."
cd "$(dirname "$0")/apps/api"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

echo "Starting Next.js frontend on :3000..."
cd "$(dirname "$0")/apps/web"
npm run dev &

wait
