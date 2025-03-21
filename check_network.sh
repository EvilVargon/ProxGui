#!/bin/bash
# Network connectivity test script

echo "==== Network Connectivity Tests ===="
echo ""

# Get host and port from token file if it exists
if [ -f "websocket_tokens.json" ]; then
    # Try to extract host and port using Python
    HOST=$(python3 -c 'import json; import sys; f=open("websocket_tokens.json"); t=json.load(f); k=list(t.keys())[0] if t else None; print(t[k].get("host", "") if k else "")' 2>/dev/null)
    PORT=$(python3 -c 'import json; import sys; f=open("websocket_tokens.json"); t=json.load(f); k=list(t.keys())[0] if t else None; print(t[k].get("port", "") if k else "")' 2>/dev/null)
    
    # If that failed, try the nested data structure
    if [ -z "$HOST" ]; then
        HOST=$(python3 -c 'import json; import sys; f=open("websocket_tokens.json"); t=json.load(f); k=list(t.keys())[0] if t else None; print(t[k]["data"]["host"] if k and "data" in t[k] else "")' 2>/dev/null)
        PORT=$(python3 -c 'import json; import sys; f=open("websocket_tokens.json"); t=json.load(f); k=list(t.keys())[0] if t else None; print(t[k]["data"]["port"] if k and "data" in t[k] else "")' 2>/dev/null)
    fi
    
    if [ -n "$HOST" ]; then
        echo "Found server in token file: $HOST:$PORT"
    fi
else
    echo "No token file found"
fi

# If we couldn't get host/port from token file, try .env
if [ -z "$HOST" ] && [ -f ".env" ]; then
    HOST=$(grep -E "^PROXMOX_HOST" .env | cut -d= -f2)
    
    if [ -n "$HOST" ]; then
        echo "Found server in .env: $HOST"
        PORT="8006"  # Default Proxmox API port
    fi
fi

# If we still don't have a host, prompt for it
if [ -z "$HOST" ]; then
    echo "Could not determine Proxmox host automatically."
    read -p "Enter the Proxmox host IP: " HOST
    PORT="5900"  # Default VNC port
fi

echo ""
echo "Testing connectivity to $HOST..."

# Try to ping the host
echo "- Ping test: "
ping -c 1 -W 2 $HOST >/dev/null
if [ $? -eq 0 ]; then
    echo "  ✅ Host is reachable via ping"
else
    echo "  ❌ Host is NOT reachable via ping"
fi

# Test common ports with timeout
function test_port() {
    PORT=$1
    DESC=$2
    
    echo -n "- Port $PORT ($DESC): "
    
    nc -z -w 2 $HOST $PORT >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ OPEN"
    else
        echo "❌ CLOSED/BLOCKED"
    fi
}

# Test standard Proxmox and VNC ports
test_port 8006 "Proxmox API"
test_port 5900 "VNC Base"
test_port 5901 "VNC :1"
test_port 5902 "VNC :2"
test_port 5903 "VNC :3"

# Check if the specific port from tokens is different
if [ -n "$PORT" ] && [ "$PORT" != "8006" ] && [ "$PORT" != "5900" ] && [ "$PORT" != "5901" ] && [ "$PORT" != "5902" ] && [ "$PORT" != "5903" ]; then
    test_port $PORT "VNC from token"
fi

echo ""
echo "==== Local Port Check ===="
# Check if port 8765 is occupied
echo -n "- WebSocket port 8765: "
nc -z -w 1 127.0.0.1 8765 >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ LISTENING"
    lsof -i :8765 | grep LISTEN
else
    echo "❌ NOT LISTENING (websockify proxy may not be running)"
fi

echo ""
echo "==== Local Route Check ===="
# Show the route to the Proxmox host
echo "Route to $HOST:"
ip route get $HOST

echo ""
echo "==== Firewall Status ===="
# Check if firewall is enabled
which ufw >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "UFW Firewall status:"
    ufw status
else
    echo "UFW not installed"
fi

which firewalld >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Firewalld status:"
    firewall-cmd --state
else
    echo "Firewalld not installed"
fi

# Check for iptables rules
echo ""
echo "==== IPTables Rules ===="
iptables -L -n | grep -E '(5900|8765|DROP|REJECT)'

echo ""
echo "==== Connectivity Check Complete ===="
echo ""
echo "If all tests passed but VNC still doesn't work:"
echo "1. Try running the direct test: ./direct_test.py"
echo "2. Run ./fix_vnc_v3.sh to apply the latest fixes"
echo "3. Check if the Proxmox server allows VNC connections from your IP"
