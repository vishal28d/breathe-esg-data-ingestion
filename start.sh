#!/usr/bin/env bash
# =============================================================================
# start.sh — Breathe ESG Dev Startup Script
#
# Starts both the Django backend and the React (Vite) frontend in parallel.
# The backend runs on http://localhost:8000
# The frontend runs on http://localhost:5173
#
# Usage:
#   chmod +x start.sh
#   ./start.sh
#
# Requirements:
#   - Python 3.10+ with the venv created at ./venv
#   - Node.js 18+ with frontend deps installed at ./frontend/node_modules
#   - Run `pip install -r requirements.txt` first if venv is missing
#   - Run `cd frontend && npm install` first if node_modules is missing
# =============================================================================

set -e  # Exit immediately if any setup command fails

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Colour

log()   { echo -e "${CYAN}[breathe-esg]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# 1. Check Python venv
# ---------------------------------------------------------------------------
if [ ! -d "venv" ]; then
  warn "venv not found — creating one now..."
  python3 -m venv venv
  ok "venv created."
fi

# Activate venv
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  # Git Bash / MSYS on Windows
  source venv/Scripts/activate
else
  source venv/bin/activate
fi
ok "Python venv activated."

# ---------------------------------------------------------------------------
# 2. Install / verify Python deps
# ---------------------------------------------------------------------------
if [ -f "requirements.txt" ]; then
  log "Installing Python dependencies..."
  pip install -q -r requirements.txt
  ok "Python deps ready."
else
  warn "requirements.txt not found — skipping pip install."
fi

# ---------------------------------------------------------------------------
# 3. Run Django migrations
# ---------------------------------------------------------------------------
log "Running Django migrations..."
python manage.py migrate --run-syncdb 2>&1 | tail -5
ok "Migrations applied."

# ---------------------------------------------------------------------------
# 4. Load fixtures (idempotent — skips if already loaded due to unique_together)
# ---------------------------------------------------------------------------
log "Loading initial fixtures..."
python manage.py loaddata api/fixtures/initial_data.json 2>&1 || warn "Fixture load skipped (may already be loaded)."

# ---------------------------------------------------------------------------
# 5. Check frontend node_modules
# ---------------------------------------------------------------------------
if [ ! -d "frontend/node_modules" ]; then
  log "node_modules not found — running npm install..."
  cd frontend && npm install && cd ..
  ok "Frontend deps installed."
fi

# ---------------------------------------------------------------------------
# 6. Start backend (background) and frontend (background)
# ---------------------------------------------------------------------------
log "Starting Django backend on http://localhost:8000 ..."
python manage.py runserver 8000 &
BACKEND_PID=$!
ok "Backend started (PID $BACKEND_PID)"

log "Starting React frontend on http://localhost:5173 ..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..
ok "Frontend started (PID $FRONTEND_PID)"

# ---------------------------------------------------------------------------
# 7. Trap Ctrl+C to cleanly stop both processes
# ---------------------------------------------------------------------------
cleanup() {
  echo ""
  log "Shutting down..."
  kill "$BACKEND_PID" 2>/dev/null && ok "Backend stopped."
  kill "$FRONTEND_PID" 2>/dev/null && ok "Frontend stopped."
  exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Breathe ESG is running!${NC}"
echo -e "${GREEN}  Backend:  http://localhost:8000${NC}"
echo -e "${GREEN}  Frontend: http://localhost:5173${NC}"
echo -e "${GREEN}  Admin:    http://localhost:8000/admin${NC}"
echo -e "${GREEN}            (user: admin / pass: admin)${NC}"
echo -e "${GREEN}  Press Ctrl+C to stop both servers${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Wait for either process to exit
wait "$BACKEND_PID" "$FRONTEND_PID"
