#!/bin/bash
# Super Fix for VNC connections - attempts all known fixes

echo "======================================================="
echo "📡 SUPER FIX for VNC Console Connections 📡"
echo "======================================================="
echo ""

# Detect OS and environment
PYTHON_VERSION=$(python3 --version 2>/dev/null || python --version 2>/dev/null)
DISTRO=$(cat /etc/*-release 2>/dev/null | grep -E "^ID=" | cut -d= -f2 | tr -d '"')
IS_DOCKER=$(grep -q "docker" /proc/1/cgroup 2>/dev/null && echo "YES" || echo "NO")

echo "System Info:"
echo "- Python: $PYTHON_VERSION"
echo "- Distro: $DISTRO"
echo "- Docker: $IS_DOCKER"
echo ""

# Stop all potentially running services
echo "1️⃣ Stopping any running proxy servers..."
pkill -f "python.*websockify_proxy.py" 2>/dev/null || true
pkill -f "websockify" 2>/dev/null || true
echo "✅ Done"
echo ""

# Verify network connection to Proxmox
echo "2️⃣ Checking network connectivity..."
# Try to find Proxmox host from token file
PROXMOX_HOST=$(python3 -c 'import json, os; file=os.path.join(os.getcwd(), "websocket_tokens.json"); host=""; port=""; 
try:
    if os.path.exists(file):
        with open(file) as f:
            tokens = json.load(f)
            if tokens:
                token_id = list(tokens.keys())[0]
                token_data = tokens[token_id]
                # Check for top-level host
                host = token_data.get("host", "")
                # Check for nested data
                if not host and "data" in token_data and isinstance(token_data["data"], dict):
                    host = token_data["data"].get("host", "")
    print(host)
except Exception:
    print("")
' 2>/dev/null)

if [ -z "$PROXMOX_HOST" ]; then
    # Try env file
    if [ -f ".env" ]; then
        PROXMOX_HOST=$(grep -E "^PROXMOX_HOST" .env | cut -d= -f2 | tr -d '"' || echo "")
    fi
fi

if [ -n "$PROXMOX_HOST" ]; then
    echo "Found Proxmox host: $PROXMOX_HOST"
    # Try ping
    ping -c 1 -W 2 $PROXMOX_HOST >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Proxmox host is reachable via ping"
    else
        echo "⚠️ WARNING: Proxmox host is NOT reachable via ping"
    fi
    
    # Try connecting to VNC port (5900)
    nc -z -w 2 $PROXMOX_HOST 5900 >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ VNC port 5900 is reachable"
    else
        echo "⚠️ WARNING: VNC port 5900 is NOT reachable - check firewall settings!"
    fi
else
    echo "⚠️ Could not determine Proxmox host address"
fi
echo ""

# Install dependencies
echo "3️⃣ Installing required dependencies..."
pip install websockify simple-websocket-server numpy
echo "✅ Dependencies installed"
echo ""

# Fix token structure
echo "4️⃣ Fixing token structure in websocket_tokens.json..."
rm -f websocket_tokens.json
echo "{}" > websocket_tokens.json
chmod 644 websocket_tokens.json
echo "✅ Token file reset"
echo ""

# Update to remove nested data structure
echo "5️⃣ Fixing code to handle different token structures..."
# Update the lookup method to handle both formats
grep -q "Using nested data format" websockify_proxy.py
if [ $? -ne 0 ]; then
    echo "Updating websockify_proxy.py to handle nested data..."
    sed -i 's/# Extract connection information/# Extract connection information - handle both formats\n                # Format 1: {'"'"'host'"'"': '"'"'...'"'"', '"'"'port'"'"': '"'"'...'"'"'}\n                # Format 2: {'"'"'data'"'"': {'"'"'host'"'"': '"'"'...'"'"', '"'"'port'"'"': '"'"'...'"'"'}}/' websockify_proxy.py
    sed -i '/host = token_data.get.*port = token_data.get/a\                # Check if we are dealing with the nested format\n                if not host and '"'"'data'"'"' in token_data and isinstance(token_data['"'"'data'"'"'], dict):\n                    data = token_data['"'"'data'"'"']\n                    host = data.get('"'"'host'"'"', '"'"''"'"')\n                    port = data.get('"'"'port'"'"', 0)\n                    logger.info(f"Using nested data format: host={host}, port={port}")' websockify_proxy.py
    echo "✅ Code updated"
else
    echo "✅ Code already updated"
fi
echo ""

# Create the final structure fix application
echo "6️⃣ Creating token structure fix application..."
cat > fix_tokens_app.py << 'EOF'
#!/usr/bin/env python3
"""Quick token structure fix"""
import json
import os
import sys

def fix_tokens(file_path):
    """Fix the token structure"""
    if not os.path.exists(file_path):
        print(f"Token file not found: {file_path}")
        # Create empty file
        with open(file_path, 'w') as f:
            json.dump({}, f)
        return False
    
    try:
        # Read tokens
        with open(file_path, 'r') as f:
            try:
                tokens = json.load(f)
            except json.JSONDecodeError:
                print("Invalid JSON in token file. Creating empty file.")
                with open(file_path, 'w') as f:
                    json.dump({}, f)
                return False
        
        print(f"Found {len(tokens)} tokens")
        fixed = False
        
        # Process tokens
        for token_id, token_data in tokens.items():
            if 'data' in token_data and isinstance(token_data['data'], dict):
                # Fix nested data structure
                data = token_data['data']
                tokens[token_id] = {
                    'ticket': data.get('ticket', ''),
                    'host': data.get('host', ''),
                    'port': data.get('port', ''),
                    'node': data.get('node', ''),
                    'vmid': data.get('vmid', ''),
                    'vmtype': data.get('vmtype', ''),
                    'cert': data.get('cert'),
                    'created_at': token_data.get('created_at', 0)
                }
                fixed = True
                print(f"Fixed token {token_id}")
        
        # Write back
        if fixed or not tokens:
            with open(file_path, 'w') as f:
                json.dump(tokens, f, indent=2)
            print("Saved updated tokens")
        else:
            print("No changes needed")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Fixing token structure...")
    token_file = os.path.join(os.getcwd(), 'websocket_tokens.json')
    if fix_tokens(token_file):
        print("✅ Token structure fixed")
    else:
        print("⚠️ Failed to fix token structure")
EOF

chmod +x fix_tokens_app.py
./fix_tokens_app.py
echo ""

# Start the proxy
echo "7️⃣ Starting websockify proxy with debugging..."
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
echo ""

# Check port 8765
echo "8️⃣ Verifying port 8765 is in use..."
netstat -tuln | grep 8765
if [ $? -eq 0 ]; then
    echo "✅ Port 8765 is in use (as expected)"
else
    echo "❌ Port 8765 is NOT in use - websockify may have failed to start"
    
    # Check for common issues
    if lsof -i :8765 >/dev/null 2>&1; then
        echo "⚠️ Another process is using port 8765"
        lsof -i :8765
    else
        echo "Port 8765 is available but websockify is not listening"
    fi
fi
echo ""

# Final configuration details
echo "======================================================="
echo "✅ SUPER FIX COMPLETED"
echo "======================================================="
echo ""
echo "If you still experience connection issues:"
echo ""
echo "1) Try running the direct connection test:"
echo "   ./direct_test.py"
echo ""
echo "2) Check network connectivity to your Proxmox server:"
echo "   ./check_network.sh"
echo ""
echo "3) Check the websockify logs for errors:"
echo "   tail -f websockify.log"
echo ""
echo "4) Ensure port 5900 (and similar VNC ports) are open on your Proxmox server"
echo ""
echo "5) Start your Flask application with:"
echo "   python run.py"
echo ""
echo "======================================================="
echo "Problem still not resolved? Try a completely fresh start:"
echo "1) Stop all processes"
echo "2) Delete websocket_tokens.json"
echo "3) Restart both the websockify proxy and Flask app"
echo "======================================================="
