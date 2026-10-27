#!/bin/bash

cd /Users/gs/Chatgpt/Dermamatrix-AI/dermamatrix-ai || exit 1

echo "Checking port 8000..."

PIDS=$(lsof -tiTCP:8000 -sTCP:LISTEN)

if [ -n "$PIDS" ]; then
    echo "Stopping previous DermaMatrix server..."
    kill $PIDS 2>/dev/null
    sleep 2

    PIDS=$(lsof -tiTCP:8000 -sTCP:LISTEN)

    if [ -n "$PIDS" ]; then
        echo "Force stopping stale server..."
        kill -9 $PIDS 2>/dev/null
        sleep 1
    fi
fi

source .venv/bin/activate

echo "Starting DermaMatrix..."
exec bash backend/scripts/run_app.sh
