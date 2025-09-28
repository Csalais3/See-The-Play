#!/bin/bash
# quick_start.sh - Launch SeeThePlay with one command

set -e  # Exit on error

echo "🏈 SeeThePlay - Quick Start"
echo "================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Fix frontend filename if needed
echo -e "${BLUE}📝 Fixing frontend file structure...${NC}"
if [ -f "frontend/src/app.js" ]; then
    mv frontend/src/app.js frontend/src/App.js 2>/dev/null || true
    echo -e "${GREEN}✅ Fixed App.js filename${NC}"
fi

# 2. Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${BLUE}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# 3. Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# 4. Install Python dependencies
echo -e "${BLUE}📚 Installing Python dependencies...${NC}"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet pulse-mock
echo -e "${GREEN}✅ Python dependencies installed${NC}"

# 5. Create necessary directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p backend/logs
mkdir -p backend/db
echo -e "${GREEN}✅ Directories created${NC}"

# 6. Create .env files if they don't exist
if [ ! -f "backend/.env" ]; then
    echo -e "${BLUE}📝 Creating backend .env file...${NC}"
    cat > backend/.env << EOF
API_HOST=0.0.0.0
API_PORT=8000
PULSE_API_URL=http://localhost:1339
CEDAR_ENABLED=true
LOG_LEVEL=INFO
EVENT_SIMULATION_SPEED=5
DATABASE_URL=sqlite:///./seetheplay.db
EOF
    echo -e "${GREEN}✅ Created backend/.env${NC}"
fi

if [ ! -f "frontend/.env.local" ]; then
    echo -e "${BLUE}📝 Creating frontend .env.local file...${NC}"
    cat > frontend/.env.local << EOF
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
EOF
    echo -e "${GREEN}✅ Created frontend/.env.local${NC}"
fi

# 7. Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${BLUE}📦 Installing frontend dependencies...${NC}"
    cd frontend
    npm install --silent
    cd ..
    echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
fi

# 8. Stop any existing services on the ports
echo -e "${BLUE}🛑 Checking for existing services...${NC}"
lsof -ti:1339 | xargs kill -9 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
echo -e "${GREEN}✅ Ports cleared${NC}"

# 9. Start Pulse Mock in background
echo -e "${BLUE}🚀 Starting Pulse Mock server...${NC}"
python -m pulse_mock.server --host localhost --port 1339 > backend/logs/pulse_mock.log 2>&1 &
PULSE_PID=$!
echo $PULSE_PID > backend/logs/pulse_mock.pid
sleep 2

# Test Pulse Mock
if curl -s http://localhost:1339/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Pulse Mock running (PID: $PULSE_PID)${NC}"
else
    echo -e "${YELLOW}⚠️  Pulse Mock might not be ready yet${NC}"
fi

# 10. Start Backend in background
echo -e "${BLUE}🔥 Starting backend server...${NC}"
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > logs/backend.pid
cd ..
sleep 3

# Test Backend
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend running (PID: $BACKEND_PID)${NC}"
else
    echo -e "${YELLOW}⚠️  Backend might not be ready yet${NC}"
fi

# 11. Start Frontend in background
echo -e "${BLUE}🎨 Starting frontend...${NC}"
cd frontend
npm start > ../backend/logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../backend/logs/frontend.pid
cd ..

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}🎉 SeeThePlay is starting!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${BLUE}🌐 Services:${NC}"
echo -e "   • Frontend:     ${GREEN}http://localhost:3000${NC}"
echo -e "   • Backend API:  ${GREEN}http://localhost:8000${NC}"
echo -e "   • API Docs:     ${GREEN}http://localhost:8000/docs${NC}"
echo -e "   • Pulse Mock:   ${GREEN}http://localhost:1339${NC}"
echo -e "   • WebSocket:    ${GREEN}ws://localhost:8000/ws${NC}"
echo ""
echo -e "${BLUE}📊 Logs:${NC}"
echo -e "   • Backend:    tail -f backend/logs/backend.log"
echo -e "   • Pulse Mock: tail -f backend/logs/pulse_mock.log"
echo -e "   • Frontend:   tail -f backend/logs/frontend.log"
echo ""
echo -e "${BLUE}⏳ Waiting for frontend to compile...${NC}"
echo -e "${YELLOW}   (This may take 30-60 seconds)${NC}"
echo ""

# Wait for frontend to be ready (check every 2 seconds for 30 seconds max)
for i in {1..15}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is ready!${NC}"
        break
    fi
    sleep 2
    echo -e "${YELLOW}   Still waiting... ($((i*2))s)${NC}"
done

echo ""
echo -e "${GREEN}🚀 SeeThePlay is now running!${NC}"
echo ""
echo -e "${BLUE}📱 Open your browser to:${NC}"
echo -e "   ${GREEN}http://localhost:3000${NC}"
echo ""
echo -e "${BLUE}🛑 To stop all services, run:${NC}"
echo -e "   ${YELLOW}./scripts/stop_services.sh${NC}"
echo ""
echo -e "${BLUE}📖 Or kill individual processes:${NC}"
echo -e "   kill $PULSE_PID      # Pulse Mock"
echo -e "   kill $BACKEND_PID    # Backend"
echo -e "   kill $FRONTEND_PID   # Frontend"
echo ""
echo -e "${GREEN}🏆 Ready for demo!${NC}"