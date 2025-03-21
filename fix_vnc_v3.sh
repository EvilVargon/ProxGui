#!/bin/bash
# VNC Fix Script - Version 3 with additional structure fixes

echo "==============================================="
echo "Fixing VNC Connection Issues (V3)"
echo "==============================================="
echo ""

# 1. Kill any existing processes
echo "[1] Stopping any running servers..."
pkill -f "python.*websockify_proxy.py" 2>/dev/null || true
pkill -f "websockify" 2>/dev/null || true

# 2. Reset or fix the token file
if [ -f "websocket_tokens.json" ]; then
    echo ""
    echo "[2] Fixing token structure..."
    ./fix_token_structure.py
else
    echo ""
    echo "[2] Creating new token file..."
    echo "{}" > websocket_tokens.json
    chmod 644 websocket_tokens.json
    echo "✅ Token file created"
fi

# 3. Install dependencies
echo ""
echo "[3] Installing dependencies..."
pip install websockify numpy simple-websocket-server
echo "✅ Dependencies installed"

# 4. Test token file structure
echo ""
echo "[4] Testing token file..."
python -c "import json; f=open('websocket_tokens.json'); data=json.load(f); print('✅ Token file has valid JSON structure')" || {
    echo "❌ Token file has invalid JSON. Creating empty token file..."
    echo "{}" > websocket_tokens.json
}

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

# 6. Check if port 8765 is available
echo ""
echo "[6] Checking if port 8765 is in use by websockify..."
netstat -tuln | grep 8765 || {
    echo "❌ Port 8765 is NOT in use - websockify may have failed to start"
    echo "Checking for error in log:"
    tail -n 20 websockify.log
}

# 7. Test direct connectivity to Proxmox
echo ""
echo "[7] Testing direct connectivity to Proxmox..."
PROXMOX_HOST=$(grep -E "^PROXMOX_HOST" .env 2>/dev/null | cut -d= -f2)

if [ -z "$PROXMOX_HOST" ]; then
    # Try to get host from token file
    PROXMOX_HOST=$(python3 -c "import json; f=open('websocket_tokens.json'); data=json.load(f); print(list(data.values())[0].get('host', '') if data else '')" 2>/dev/null)
    
    if [ -z "$PROXMOX_HOST" ]; then
        echo "⚠️ Could not determine Proxmox host. Please enter it manually:"
        read -p "Proxmox host IP: " PROXMOX_HOST
    else
        echo "Found Proxmox host in token file: $PROXMOX_HOST"
    fi
else
    echo "Found Proxmox host in .env: $PROXMOX_HOST"
fi

# Test TCP connection to port 5900
if [ -n "$PROXMOX_HOST" ]; then
    echo "Testing connection to $PROXMOX_HOST:5900..."
    nc -z -w 5 $PROXMOX_HOST 5900 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Successfully connected to $PROXMOX_HOST:5900"
    else
        echo "❌ Cannot connect to $PROXMOX_HOST:5900 - VNC connections may fail"
        echo "   Check firewall settings or network connectivity"
    fi
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
echo "If issues persist, try these debugging steps:"
echo "1. Run ./debug_vnc.sh for detailed diagnostics"
echo "2. Check websockify.log for errors"
echo "3. Try a direct test: python test_vnc_connectivity.py --all-tokens"
echo ""

# End with status of the websockify proxy
if kill -0 $PROXY_PID 2>/dev/null; then
    echo "Websockify proxy is running with PID $PROXY_PID"
    echo "Log file: websockify.log"
else
    echo "❌ WARNING: Websockify proxy is NOT running!"
    echo "Check websockify.log for errors"
fi
