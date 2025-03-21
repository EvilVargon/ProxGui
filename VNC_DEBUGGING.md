# VNC Console Connectivity Troubleshooting Guide

This guide will help you diagnose and fix VNC console connection issues in the Proxmox User Portal.

## Quick Fix

For a comprehensive fix that addresses most common issues:

```bash
./super_fix.sh
```

Then restart your Flask application:

```bash
python run.py
```

## Diagnosing the Problem

If the quick fix didn't work, follow these steps to pinpoint the issue:

### 1. Check Network Connectivity

First, verify that your machine can connect to the Proxmox server:

```bash
./check_network.sh
```

This will test connectivity to various ports on your Proxmox server. Pay special attention to:
- Whether port 5900 (the VNC port) is reachable
- Whether the Proxmox API port (8006) is reachable
- If any firewalls might be blocking connections

### 2. Test Direct VNC Connection

Try connecting directly to the VNC port on your Proxmox server:

```bash
./direct_test.py
```

This will:
- Find connection details from your token file
- Try to establish a direct TCP connection to the VNC port
- Report success or failure

If this fails, the issue is likely with network connectivity to the Proxmox VNC port.

### 3. Check Websockify Proxy

Verify that the websockify proxy is running and listening on port 8765:

```bash
lsof -i :8765
```

You should see a Python process listening on this port. If not, start the proxy:

```bash
python websockify_proxy.py > websockify.log 2>&1 &
```

### 4. Examine Token Structure

The token file might have an invalid structure. Check it with:

```bash
./debug_websockify.py display
```

The token structure should look like:

```json
{
  "token-uuid": {
    "host": "192.168.x.x",
    "port": "5900",
    "ticket": "VNC-TICKET-STRING",
    "created_at": 1234567890.123
  }
}
```

If you see a nested "data" object, fix it:

```bash
./fix_token_structure.py
```

### 5. Check WebSocket Logs

Examine the websockify logs for errors:

```bash
tail -f websockify.log
```

Look for:
- Connection attempts
- Connection failures
- Token validation issues
- Direct connection test results

### 6. Browser Console Logs

Open your browser's developer console (F12) when attempting to connect to the VNC console. Look for:
- WebSocket connection attempts and errors
- JavaScript errors related to noVNC or WebSockets
- Any messages about "Connection closed"

## Common Issues and Solutions

### WebSocket Connection Failed

**Symptoms**: Browser shows "Connection closed" or "Failed to connect to WebSocket"

**Solutions**:
1. Make sure the websockify proxy is running
2. Check if port 8765 is in use by another application
3. Try a different browser

### Token Not Found

**Symptoms**: Logs show "Token not found" or "Invalid token"

**Solutions**:
1. Reset the token file: `rm websocket_tokens.json && echo "{}" > websocket_tokens.json`
2. Check file permissions: `chmod 644 websocket_tokens.json`
3. Apply the token structure fix: `./fix_token_structure.py`

### VNC Server Not Reachable

**Symptoms**: Logs show "Could not establish direct connection" or similar

**Solutions**:
1. Check if the Proxmox VNC port is open: `nc -z -v <proxmox-ip> 5900`
2. Verify Proxmox firewall settings allow connections from your machine
3. Check if Proxmox is configured to allow VNC connections

### Wrong Port Number

**Symptoms**: Connection attempts go to the wrong port

**Solutions**:
1. VNC ports in Proxmox typically start at 5900 and increment by VM ID
2. Try different ports: 5900, 5901, 5902, etc.
3. Check exact port in logs: `grep "port" websockify.log`

### Browser Security Issues

**Symptoms**: Console attempts to load but fails with security errors

**Solutions**:
1. Try using HTTP instead of HTTPS for local development
2. Check if browser is blocking mixed content
3. Try a different browser (Firefox sometimes works better than Chrome for WebSockets)

## Advanced Troubleshooting

### Manual WebSocket Test

You can test the WebSocket connection directly:

```bash
# Install wscat if needed
npm install -g wscat

# Connect to the WebSocket server
wscat -c "ws://localhost:8765/api/ws/vnc?token=<your-token>&type=qemu"
```

If this fails but the websockify proxy is running, there might be an issue with the proxy configuration.

### Direct noVNC Test

You can also use the standalone noVNC viewer to test connectivity:

1. Download noVNC: `git clone https://github.com/novnc/noVNC.git`
2. Start the Proxmox VNC proxy: `pvesh create /nodes/<node>/qemu/<vmid>/vncproxy`
3. Use the noVNC viewer to connect directly: `./noVNC/vnc.html?host=<proxmox-ip>&port=<vnc-port>&password=<ticket>`

### Check for SSL/Certificate Issues

If your Proxmox server uses a self-signed certificate, it might cause issues with the VNC connection:

1. Verify the certificate in the browser: Visit `https://<proxmox-ip>:8006` and accept the certificate
2. Try adding `verify: false` to your Proxmox API connection settings
3. Add the certificate to your trusted root certificates

## Proxmox-Specific Settings

### Check VM Console Settings

1. Log in to Proxmox web interface
2. Select your VM
3. Go to Hardware > Display
4. Ensure "Console" is set to "VNC" or "Default"
5. Note the port setting if present

### Test with Proxmox Web Console

Try using the built-in Proxmox web console:

1. Log in to Proxmox web interface
2. Select your VM
3. Click on "Console" tab
4. If this works but your app doesn't, the issue is in your WebSocket proxy

## Final Checklist

If you've tried everything and still have issues:

1. ✅ Proxmox API is reachable and returning VNC ticket
2. ✅ Direct TCP connection to VNC port works
3. ✅ Websockify proxy is running and listening on port 8765
4. ✅ Token file has the correct structure
5. ✅ Browser can establish WebSocket connections
6. ✅ No firewall or network issues between components
7. ✅ VNC is properly configured on the Proxmox VM

If all these check out but you still have issues, please contact support with your detailed logs and diagnostic information.
