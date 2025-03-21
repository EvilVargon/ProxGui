#!/bin/bash
# Simple VNC Fix - Just the basic websockify proxy

echo "Starting a simple websockify proxy..."

# Get Proxmox host from .env file
PROXMOX_HOST=$(grep -E "^PROXMOX_HOST" .env 2>/dev/null | cut -d= -f2 | tr -d '"')

if [ -z "$PROXMOX_HOST" ]; then
    echo "Could not find PROXMOX_HOST in .env"
    echo "Please enter your Proxmox host IP address:"
    read PROXMOX_HOST
fi

# Stop any running websockify processes
pkill -f websockify 2>/dev/null || true

# Ask for VM ID if it wasn't found
echo "Which VM ID do you want to connect to?"
read VMID

# Ask for target port
echo "Which port would you like to connect to? (default: 5900)"
read PORT
PORT=${PORT:-5900}

echo "Starting websockify proxy on port 8765 pointing to $PROXMOX_HOST:$PORT..."
websockify 8765 $PROXMOX_HOST:$PORT &
WEBSOCKIFY_PID=$!

echo "Websockify started with PID $WEBSOCKIFY_PID"
echo ""
echo "Now you can:"
echo "1. Start your Flask application: python run.py"
echo "2. Go to the VM details page and click 'Connect'"
echo ""
echo "Press Enter to stop the websockify proxy..."
read

echo "Stopping websockify proxy..."
kill $WEBSOCKIFY_PID
