#!/bin/bash
# setup.sh - FIXED VERSION - Complete setup script for SeeThePlay

echo "🏈 Setting up SeeThePlay - Transparent Sports Predictions"
echo "=================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+ and try again."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ and try again."
    exit 1
fi

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install pulse-mock
echo "🎯 Installing PrizePicks Pulse Mock..."
pip install pulse-mock

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/logs
mkdir -p backend/db

# Check if Pulse Mock is already running
if lsof -Pi :1339 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Pulse Mock is already running on port 1339"
else
    # Start the pulse-mock server in background
    echo "🚀 Starting Pulse Mock server on port 1339..."
    python3 -m pulse_mock.server --host localhost --port 1339 > backend/logs/pulse_mock.log 2>&1 &
    PULSE_PID=$!
    echo "✅ Pulse Mock server started (PID: $PULSE_PID)"
    
    # Save PID for later cleanup
    echo $PULSE_PID > backend/logs/pulse_mock.pid
fi

# Wait for Pulse Mock to be ready
echo "⏳ Waiting for Pulse Mock to be ready..."
sleep 3

# Test Pulse Mock connection
if curl -s http://localhost:1339/health > /dev/null 2>&1; then
    echo "✅ Pulse Mock is responding"
else
    echo "⚠️  Pulse Mock might not be ready yet, but continuing..."
fi

# Install frontend dependencies
echo "🎨 Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Create .env file if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend .env file..."
    cat > backend/.env << EOF
API_HOST=0.0.0.0
API_PORT=8000
PULSE_API_URL=http://localhost:1339
CEDAR_ENABLED=true
LOG_LEVEL=INFO
EVENT_SIMULATION_SPEED=5
DATABASE_URL=sqlite:///./seetheplay.db
EOF
    echo "✅ Created backend/.env"
fi

# Create frontend .env file if it doesn't exist
if [ ! -f frontend/.env.local ]; then
    echo "📝 Creating frontend .env.local file..."
    cat > frontend/.env.local << EOF
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
EOF
    echo "✅ Created frontend/.env.local"
fi

# Start the backend
echo "🔥 Starting SeeThePlay backend..."
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
echo $BACKEND_PID > logs/backend.pid
cd ..

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
sleep 5

# Test backend connection
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Backend is responding"
else
    echo "⚠️  Backend might not be ready yet"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌟 SeeThePlay is now running:"
echo "   • Backend API: http://localhost:8000"
echo "   • API Docs: http://localhost:8000/docs"
echo "   • Pulse Mock API: http://localhost:1339"
echo "   • WebSocket: ws://localhost:8000/ws"
echo ""
echo "🎨 To start the frontend (in a new terminal):"
echo "   cd frontend"
echo "   npm start"
echo ""
echo "📊 View logs:"
echo "   • Backend: tail -f backend/logs/backend.log"
echo "   • Pulse Mock: tail -f backend/logs/pulse_mock.log"
echo ""
echo "🛑 To stop services:"
echo "   kill \$(cat backend/logs/backend.pid)"
echo "   kill \$(cat backend/logs/pulse_mock.pid)"
echo ""
echo "🏆 Demo Flow for Judges:"
echo "   1. Open frontend → Show live dashboard with predictions"
echo "   2. Trigger weather/scoring scenarios"
echo "   3. Use Cedar AI chat to ask about predictions"
echo "   4. Highlight real-time updates and explainability"
echo ""