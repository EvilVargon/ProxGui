#!/bin/bash
# Script to fix VNC connection issues

echo "Fixing VNC connections..."

# Stop existing websocket servers
echo "Stopping any existing websocket servers..."
pkill -f "python.*run_websocket.py" || true

# Clean up token files
echo "Cleaning up token files..."
rm -f websocket_tokens.json debug_tokens.json

# Initialize empty token file
echo "{}" > websocket_tokens.json
chmod 644 websocket_tokens.json

echo "Starting websocket server..."
# Start the websocket server in the background
python run_websocket.py &
WEBSOCKET_PID=$!

echo "Websocket server started with PID $WEBSOCKET_PID"
echo ""
echo "VNC fix complete! Please run your Flask application and test VNC again."
echo "To restart both services use ./start.sh"
