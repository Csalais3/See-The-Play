# setup.sh - Complete setup script for SeeThePlay
#!/bin/bash

echo "🏈 Setting up SeeThePlay - Transparent Sports Predictions"
echo "=================================================="

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Install pulse-mock
echo "🎯 Installing PrizePicks Pulse Mock..."
pip install pulse-mock

# Start the pulse-mock server in background
echo "🚀 Starting Pulse Mock server..."
python -c "
from pulse_mock import create_app
app = create_app()
print('Pulse Mock server starting on localhost:1339...')
" &
PULSE_PID=$!

# Wait a moment for server to start
sleep 3

# Start the backend
echo "🔥 Starting SeeThePlay backend..."
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "✅ Setup complete!"
echo ""
echo "🌟 SeeThePlay is now running:"
echo "   • Frontend: Open the React dashboard in your browser"
echo "   • Backend API: http://localhost:8000"
echo "   • Pulse Mock API: http://localhost:1339"
echo "   • WebSocket: ws://localhost:8000/ws"
echo ""
echo "🎮 Demo Features:"
echo "   • Live game simulation with real-time events"
echo "   • ML-powered player predictions"
echo "   • Cedar AI explanations (interactive chat)"
echo "   • What-if scenarios (weather, game script changes)"
echo "   • Confidence scoring with visual indicators"
echo ""
echo "🏆 Judge Demo Flow:"
echo "   1. Show live dashboard with predictions updating"
echo "   2. Trigger scenario changes (weather/scoring)"
echo "   3. Ask Cedar AI questions about predictions"
echo "   4. Highlight explainable AI features"
echo "   5. Show technical architecture"
echo ""
echo "⚡ To stop: Press Ctrl+C"

# Keep script running
wait $BACKEND_PID
