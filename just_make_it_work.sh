#!/bin/bash
# The "Just Make It Work" VNC Solution

echo "===================================="
echo "The 'Just Make It Work' VNC Solution"
echo "===================================="
echo ""

# Stop existing processes
pkill -f websockify 2>/dev/null || true
pkill -f "python.*direct_vnc_bridge.py" 2>/dev/null || true

# Check for dependencies
if ! command -v websockify &> /dev/null; then
    echo "Installing websockify..."
    pip install websockify requests
fi

# Get parameters
PROXMOX_HOST=$(grep -E "^PROXMOX_HOST" .env 2>/dev/null | cut -d= -f2 | tr -d '"')

if [ -z "$PROXMOX_HOST" ]; then
    echo "Enter your Proxmox host IP:"
    read PROXMOX_HOST
fi

echo "This script will try two different approaches to get VNC working."
echo ""
echo "Approach 1: Direct connection to VNC port"
echo "----------------------------------------"

# Try direct connection first
python connect_test.py $PROXMOX_HOST 5900
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "Direct connection successful! Setting up websockify..."
    websockify 8765 $PROXMOX_HOST:5900 > websockify.log 2>&1 &
    WEBSOCKIFY_PID=$!
    echo "Websockify started with PID $WEBSOCKIFY_PID pointing to $PROXMOX_HOST:5900"
else
    echo "Direct connection failed."
    echo ""
    echo "Approach 2: Using Proxmox API VNC proxy"
    echo "----------------------------------------"
    
    # Start the bridge
    python direct_vnc_bridge.py &
    BRIDGE_PID=$!
    
    echo "VNC bridge started with PID $BRIDGE_PID"
    echo "It's now listening on port 8765"
fi

echo ""
echo "===================================="
echo "What to do next:"
echo "1. Start your Flask app: python run.py"
echo "2. Go to the VM details page"
echo "3. Click 'Connect' in the console section"
echo ""
echo "This terminal needs to stay open for VNC to work."
echo "Press Ctrl+C to stop the VNC connection."
echo "===================================="

# Wait for Ctrl+C
trap "echo 'Stopping VNC connection...'; kill $WEBSOCKIFY_PID 2>/dev/null; kill $BRIDGE_PID 2>/dev/null" INT
wait
