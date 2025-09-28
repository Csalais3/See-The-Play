#!/bin/bash
# debug_check.sh - Find out what's wrong

echo "🔍 Debugging SeeThePlay Issues"
echo "================================"

echo ""
echo "1️⃣ Checking backend logs for errors..."
echo "Last 30 lines:"
tail -30 backend/logs/backend.log

echo ""
echo "2️⃣ Testing API endpoints..."

echo ""
echo "📋 Teams endpoint:"
curl -s http://localhost:8000/api/predictions/teams | jq '.[0]' 2>/dev/null || curl -s http://localhost:8000/api/predictions/teams

echo ""
echo "👥 Eagles players (should show 5):"
EAGLES_ID=$(curl -s http://localhost:8000/api/predictions/teams | jq -r '.[] | select(.name=="Eagles" or .alias=="PHI") | .id' 2>/dev/null)
echo "Eagles ID: $EAGLES_ID"

if [ -n "$EAGLES_ID" ]; then
    curl -s "http://localhost:8000/api/predictions/team/${EAGLES_ID}/players?limit=5" | jq '.predictions | length' 2>/dev/null || echo "Error fetching predictions"
    curl -s "http://localhost:8000/api/predictions/team/${EAGLES_ID}/players?limit=5" | jq '.predictions[].player_name' 2>/dev/null || echo "Error getting player names"
else
    echo "❌ Could not find Eagles team ID"
fi

echo ""
echo "3️⃣ Checking WebSocket (browser console)..."
echo "Open browser console (F12) and look for:"
echo "  - WebSocket connection messages"
echo "  - 'game_initialized' message with predictions array"
echo "  - Check predictions.length in the message"

echo ""
echo "4️⃣ Quick fixes to try:"
echo "   ./scripts/stop_services.sh"
echo "   rm backend/logs/*.log"
echo "   ./scripts/quick_start.sh"