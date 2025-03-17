#!/bin/bash
# Start script for ProxGui with WebSocket server

# Start the websocket server in the background
echo "Starting WebSocket server..."
python run_websocket.py &
WEBSOCKET_PID=$!

# Start the Flask application
echo "Starting Flask application..."
python run.py

# When Flask exits, also kill the WebSocket server
echo "Stopping WebSocket server..."
kill $WEBSOCKET_PID
