#!/bin/bash
# VNC Quickstart Script - applies all fixes and starts the proxy

echo "Applying VNC Quick Fix..."

# 1. Stop existing processes
pkill -f "python.*websockify_proxy.py" 2>/dev/null || true
pkill -f "websockify" 2>/dev/null || true

# 2. Fix the token structure
python quick_fix.py

# 3. Start the websockify proxy
echo "Starting websockify proxy..."
python websockify_proxy.py > websockify.log 2>&1 &
PROXY_PID=$!

echo "Websockify proxy started with PID $PROXY_PID"
echo "Now you can run your Flask app with: python run.py"
