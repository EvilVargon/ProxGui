#!/bin/bash
# VNC Fix Script - Version 2 with additional fixes based on debugging

echo "==============================================="
echo "Fixing VNC Connection Issues (V2)"
echo "==============================================="
echo ""

# 1. Kill any existing processes
echo "[1] Stopping any running servers..."
pkill -f "python.*websockify_proxy.py" 2>/dev/null || true
pkill -f "websockify" 2>/dev/null || true

# 2. Reset the token file
echo ""
echo "[2] Resetting token file..."
rm -f websocket_tokens.json
echo "{}" > websocket_tokens.json
chmod 644 websocket_tokens.json
echo "✅ Token file reset"

# 3. Install dependencies
echo ""
echo "[3] Installing dependencies..."
pip install websockify numpy simple-websocket-server
echo "✅ Dependencies installed"

# 4. Check for connectivity to Proxmox
echo ""
echo "[4] Testing Proxmox connectivity..."
PROXMOX_HOST=$(grep -E "^PROXMOX_HOST" .env | cut -d= -f2)

if [ -z "$PROXMOX_HOST" ]; then
    echo "⚠️ Could not find PROXMOX_HOST in .env file. Using default 192.168.1.1"
    PROXMOX_HOST="192.168.1.1"
else
    echo "Found PROXMOX_HOST: $PROXMOX_HOST"
fi

# Try to ping proxmox host
ping -c 1 $PROXMOX_HOST > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Proxmox server is reachable"
else
    echo "⚠️ WARNING: Cannot ping Proxmox server - VNC connections might fail"
fi

# Check if port 8006 is reachable (standard Proxmox API port)
nc -z -w 5 $PROXMOX_HOST 8006 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Proxmox API port 8006 is reachable"
else
    echo "⚠️ WARNING: Cannot reach Proxmox API port 8006 - VNC connections might fail"
fi

# 5. Start websockify proxy with verbose logging
echo ""
echo "[5] Starting websockify proxy with verbose logging..."
python websockify_proxy.py > websockify.log 2>&1 &
PROXY_PID=$!
sleep 2

# Check if proxy is running
if kill -0 $PROXY_PID 2>/dev/null; then
    echo "✅ Websockify proxy started with PID $PROXY_PID"
else
    echo "❌ Failed to start websockify proxy"
    tail -n 10 websockify.log
fi

# 6. Create a local VNC test server for debugging
echo ""
echo "[6] Setting up a test VNC server configuration..."
mkdir -p test_vnc
# Create a dummy VNC token for testing
cat > test_vnc/token.json <<EOL
{
  "test-token": {
    "host": "localhost",
    "port": 5901,
    "ticket": "test-ticket",
    "created_at": $(date +%s)
  }
}
EOL
echo "✅ Test VNC configuration created"
echo "   Use test-token for debugging"

# 7. Check if port 8765 is available
echo ""
echo "[7] Checking if port 8765 is in use by websockify..."
netstat -tuln | grep 8765
if [ $? -eq 0 ]; then
    echo "✅ Port 8765 is in use (as expected)"
else
    echo "❌ Port 8765 is NOT in use - websockify may have failed to start"
fi

# 8. Print instructions
echo ""
echo "==============================================="
echo "Fix Complete!"
echo "==============================================="
echo ""
echo "To run your application:"
echo "1. Start the Flask application: python run.py"
echo "2. Test the VNC connection in your browser"
echo ""
echo "If issues persist, run ./debug_vnc.sh for detailed diagnostics."
echo "To test port connectivity directly: ./test_vnc_connectivity.py --host $PROXMOX_HOST --port 5900"
