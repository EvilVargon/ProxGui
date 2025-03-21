#!/bin/bash
# Start script for ProxGui with WebSocket server

# Make sure token file is initialized
echo "Initializing token file..."
if [ ! -f "websocket_tokens.json" ]; then
    echo "{}" > websocket_tokens.json
fi

# Check if websockify is installed
pip install websockify > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Installing websockify..."
    pip install websockify
fi

# Start the websockify proxy server in the background
echo "Starting WebSocket proxy server..."
python websockify_proxy.py &
WEBSOCKET_PID=$!

# Give the WebSocket server a moment to start up
sleep 2

# Start the Flask application
echo "Starting Flask application..."
python run.py

# When Flask exits, also kill the WebSocket server
echo "Stopping WebSocket server..."
kill $WEBSOCKET_PID