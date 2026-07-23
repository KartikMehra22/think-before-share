#!/usr/bin/env bash

# Exit on error
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

USE_TERMS=false
if [ "$1" == "--terms" ] || [ "$1" == "-t" ]; then
    USE_TERMS=true
fi

echo "🚀 [Dev Master Script] Preparing think-before-share development suite..."

# 0. Kill any process occupying ports 3000 or 8000
echo "🧹 [0/3] Checking and freeing ports 3000 and 8000..."
for PORT in 3000 8000; do
    PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "  ⚠️ Port $PORT is occupied by PID(s): $PIDS. Terminating..."
        kill -9 $PIDS 2>/dev/null || true
    fi
done

# 1. Setup Python Environment
echo "🐍 [1/3] Preparing Python Virtual Environment..."
cd "$ROOT_DIR/backend"
if [ ! -d ".venv" ]; then
    echo "Creating Python virtualenv (.venv)..."
    python3.12 -m venv .venv || python3 -m venv .venv
fi
source .venv/bin/activate
echo "Checking Python requirements..."
pip install -r requirements.txt

# 2. Build Frontend
echo "📦 [2/3] Building Next.js frontend..."
cd "$ROOT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    pnpm install
fi
pnpm run build

# 3. Launch Services
if [ "$USE_TERMS" = true ]; then
    echo "🖥️ [3/3] Launching services in separate macOS Terminal windows..."
    osascript -e 'tell application "Terminal" to do script "cd \"'$ROOT_DIR'/backend\" && source .venv/bin/activate && uvicorn main:app --port 8000 --reload"' >/dev/null
    sleep 2
    cd "$ROOT_DIR/frontend"
    NODE_ENV=development pnpm run dev
else
    echo "✨ [3/3] Launching services using concurrently..."
    cd "$ROOT_DIR"
    npx -y concurrently \
      --names "PYTHON,FRONTEND" \
      --prefix-colors "yellow,cyan" \
      --kill-others \
      "cd backend && source .venv/bin/activate && uvicorn main:app --port 8000 --reload" \
      "cd frontend && NODE_ENV=development pnpm run dev"
fi
