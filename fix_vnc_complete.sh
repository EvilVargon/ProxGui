#!/bin/bash
# Comprehensive fix for VNC connections

echo "===== Comprehensive VNC Connection Fix ====="
echo ""

# 1. Stop any running servers
echo "Stopping any running servers..."
pkill -f "python.*run_websocket.py" 2>/dev/null || true
pkill -f "python.*websockify_proxy.py" 2>/dev/null || true
pkill -f "websockify" 2>/dev/null || true

# 2. Install dependencies
echo "Installing dependencies..."
pip install websockify simple-websocket-server numpy

# 3. Clean up token files
echo "Cleaning up token files..."
rm -f websocket_tokens.json debug_tokens.json
echo "{}" > websocket_tokens.json
chmod 644 websocket_tokens.json

# Verify permissions on storage directory
echo "Checking data directory permissions..."
mkdir -p app/data
chmod -R 755 app/data

# 4. Check for important files
echo "Checking for required files..."
if [ ! -f "websockify_proxy.py" ]; then
    echo "ERROR: websockify_proxy.py is missing. Please make sure you have all the updated files."
    exit 1
fi

# 5. Check if port 8765 is available
echo "Checking if port 8765 is available..."
nc -z localhost 8765 2>/dev/null
if [ $? -eq 0 ]; then
    echo "WARNING: Port 8765 is already in use. You may need to free it before running the proxy."
    echo "You can use: sudo lsof -i :8765 to find what's using it."
    echo "And: kill -9 PID to kill the process."
else
    echo "Port 8765 is available."
fi

# 6. Start the websockify proxy
echo "Starting websockify proxy..."
python websockify_proxy.py &
PROXY_PID=$!

# Wait a moment to make sure it started
sleep 2

# Check if it's actually running
if kill -0 $PROXY_PID 2>/dev/null; then
    echo "Websockify proxy started successfully with PID $PROXY_PID"
else
    echo "ERROR: Websockify proxy failed to start."
    echo "Check the logs in websockify.log for more information."
    exit 1
fi

echo ""
echo "===== VNC fix complete! ====="
echo ""
echo "The websockify proxy is now running on port 8765."
echo "Start your Flask application with: python run.py"
echo "To restart both services at once, use: ./start.sh"
echo ""
echo "For debugging VNC connections, use:"
echo "  ./debug_websockify.py display         # View current tokens"
echo "  ./debug_websockify.py check-port 8765 # Check if port is in use"
echo "  ./debug_websockify.py ping host port  # Test connectivity"
echo ""
echo "For a full solution restart, use the 'start.sh' script."
