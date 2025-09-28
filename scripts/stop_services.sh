#!/bin/bash
# stop_services.sh - Stop all SeeThePlay services

echo "🛑 Stopping SeeThePlay services..."

# Stop backend
if [ -f backend/logs/backend.pid ]; then
    BACKEND_PID=$(cat backend/logs/backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        rm backend/logs/backend.pid
        echo "✅ Backend stopped"
    else
        echo "⚠️  Backend not running"
        rm backend/logs/backend.pid
    fi
else
    echo "⚠️  No backend PID file found"
fi

# Stop Pulse Mock
if [ -f backend/logs/pulse_mock.pid ]; then
    PULSE_PID=$(cat backend/logs/pulse_mock.pid)
    if kill -0 $PULSE_PID 2>/dev/null; then
        echo "Stopping Pulse Mock (PID: $PULSE_PID)..."
        kill $PULSE_PID
        rm backend/logs/pulse_mock.pid
        echo "✅ Pulse Mock stopped"
    else
        echo "⚠️  Pulse Mock not running"
        rm backend/logs/pulse_mock.pid
    fi
else
    echo "⚠️  No Pulse Mock PID file found"
fi

# Alternative: Kill by port if PIDs don't work
echo ""
echo "🔍 Checking for processes on ports..."

# Check port 8000 (backend)
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Found process on port 8000, killing..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    echo "✅ Port 8000 cleared"
fi

# Check port 1339 (pulse mock)
if lsof -Pi :1339 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Found process on port 1339, killing..."
    lsof -ti:1339 | xargs kill -9 2>/dev/null
    echo "✅ Port 1339 cleared"
fi

echo ""
echo "✅ All services stopped"