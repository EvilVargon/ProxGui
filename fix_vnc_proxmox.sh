#!/bin/bash
# Fix VNC by directly using Proxmox's built-in proxy

echo "====================================="
echo "VNC Connection Fix - Proxmox Edition"
echo "====================================="
echo ""

# 1. Stop any running websockify processes
echo "Stopping existing websockify processes..."
pkill -f "python.*websockify_proxy.py" 2>/dev/null || true
pkill -f "websockify" 2>/dev/null || true

# 2. Install dependencies
echo "Installing required dependencies..."
pip install requests websockify

# 3. Get direct VNC ticket from Proxmox
echo "Getting VNC ticket directly from Proxmox..."
OUTPUT=$(python vnc_direct_proxy.py)

if [ $? -ne 0 ]; then
    echo "❌ Failed to get VNC ticket. Please check your Proxmox credentials."
    echo "Detailed output:"
    echo "$OUTPUT"
    exit 1
fi

# Extract the host and port from the output
HOST=$(echo "$OUTPUT" | grep "Host:" | awk '{print $2}')
PORT=$(echo "$OUTPUT" | grep "Port:" | awk '{print $2}' | head -1)

if [ -z "$HOST" ] || [ -z "$PORT" ]; then
    echo "❌ Failed to parse host or port from the output."
    echo "Detailed output:"
    echo "$OUTPUT"
    exit 1
fi

echo "✅ Successfully obtained VNC ticket"
echo "  Host: $HOST"
echo "  Port: $PORT"

# 4. Start websockify with the direct Proxmox credentials
echo "Starting websockify..."
websockify 8765 "$HOST:$PORT" > websockify.log 2>&1 &
WEBSOCKIFY_PID=$!

sleep 2

# Check if websockify is running
if kill -0 $WEBSOCKIFY_PID 2>/dev/null; then
    echo "✅ Websockify started with PID $WEBSOCKIFY_PID"
else
    echo "❌ Failed to start websockify"
    cat websockify.log
    exit 1
fi

echo ""
echo "====================================="
echo "✅ VNC Fix Complete!"
echo "====================================="
echo ""
echo "To access the VNC console:"
echo "1. Start your Flask application: python run.py"
echo "2. Go to the VM details page"
echo "3. Click 'Connect' in the VNC console section"
echo ""
echo "If you still have issues:"
echo "1. Check websockify.log for errors"
echo "2. Try running vnc_direct_proxy.py manually"
echo "3. Use a standalone VNC client to test the direct connection"
