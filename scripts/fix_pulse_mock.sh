#!/bin/bash
# fix_pulse_mock.sh - Fix Pulse Mock server issues

echo "🔧 Fixing Pulse Mock Server..."

# 1. Stop current Pulse Mock
echo "🛑 Stopping current Pulse Mock..."
lsof -ti:1339 | xargs kill -9 2>/dev/null
sleep 1

# 2. Test if pulse-mock is installed correctly
echo "📦 Checking pulse-mock installation..."
python3 -c "import pulse_mock; print('✅ pulse-mock installed')" 2>/dev/null || {
    echo "❌ pulse-mock not found, installing..."
    pip install pulse-mock
}

# 3. Start Pulse Mock with correct command
echo "🚀 Starting Pulse Mock server..."
python3 -m pulse_mock.server --host localhost --port 1339 > backend/logs/pulse_mock.log 2>&1 &
PULSE_PID=$!
echo $PULSE_PID > backend/logs/pulse_mock.pid
sleep 3

# 4. Test Pulse Mock endpoints
echo ""
echo "🧪 Testing Pulse Mock endpoints..."

# Test 1: Check if server is up
if curl -s http://localhost:1339/health > /dev/null 2>&1; then
    echo "✅ Pulse Mock server is running"
else
    echo "❌ Pulse Mock server not responding on :1339"
    echo "📋 Check logs: tail -20 backend/logs/pulse_mock.log"
    exit 1
fi

# Test 2: Try different team endpoints
echo ""
echo "Testing team endpoints..."

# Try base endpoint
echo "1. Testing /teams..."
curl -s http://localhost:1339/teams 2>/dev/null && echo "" || echo "❌ /teams failed"

# Try NFL specific
echo "2. Testing /leagues/NFL/teams..."
curl -s http://localhost:1339/leagues/NFL/teams 2>/dev/null && echo "" || echo "❌ /leagues/NFL/teams failed"

# Try v1 endpoint
echo "3. Testing /v1/leagues/NFL/teams..."
curl -s http://localhost:1339/v1/leagues/NFL/teams 2>/dev/null && echo "" || echo "❌ /v1/leagues/NFL/teams failed"

# 5. Show what endpoints ARE available
echo ""
echo "📋 Available Pulse Mock endpoints:"
python3 << 'EOF'
import pulse_mock
from pulse_mock import create_app

app = create_app()

print("\nRegistered routes:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.methods} {rule.rule}")
EOF

echo ""
echo "💡 Fix: Update api_clients.py to use correct endpoint"
echo ""
echo "Current line in api_clients.py:"
grep -n "def get_teams" backend/utils/api_clients.py -A 5 | head -7

echo ""
echo "🔄 Now restart backend..."