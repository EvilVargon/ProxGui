#!/usr/bin/env python3
"""
Direct VNC Bridge - authenticates with Proxmox API and creates a websockify connection

This script:
1. Authenticates with Proxmox API
2. Gets a VNC proxy ticket
3. Creates a websockify server to bridge the connection
"""
import os
import sys
import json
import requests
import time
import threading
import socket
import argparse
import subprocess
import signal
import atexit

# Global variables
proxy_process = None

def cleanup():
    """Clean up resources on exit"""
    global proxy_process
    if proxy_process:
        print("Stopping websockify process...")
        try:
            proxy_process.terminate()
        except:
            pass

def get_proxmox_credentials():
    """Get Proxmox credentials from .env file"""
    credentials = {}
    
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    credentials[key] = value.strip().strip('"')
    
    return credentials

def get_vnc_proxy_ticket(host, user, password, node, vmid, vmtype='qemu'):
    """
    Get a VNC proxy ticket from Proxmox API
    """
    print(f"Connecting to Proxmox API at {host}...")
    
    # Define URLs
    auth_url = f"https://{host}:8006/api2/json/access/ticket"
    
    # Authentication data
    auth_data = {
        "username": user,
        "password": password
    }
    
    try:
        # Disable SSL warnings for self-signed certificates
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        
        # First authenticate and get a ticket
        print("Authenticating...")
        auth_response = requests.post(auth_url, data=auth_data, verify=False)
        
        if auth_response.status_code != 200:
            print(f"Authentication failed: {auth_response.status_code}")
            print(f"Error: {auth_response.text}")
            return None
        
        # Extract authentication data
        auth_data = auth_response.json()['data']
        ticket = auth_data['ticket']
        csrf_token = auth_data['CSRFPreventionToken']
        
        print("Authentication successful!")
        
        # Now get a VNC proxy ticket
        if vmtype == 'qemu':
            proxy_url = f"https://{host}:8006/api2/json/nodes/{node}/qemu/{vmid}/vncproxy"
        else:
            proxy_url = f"https://{host}:8006/api2/json/nodes/{node}/lxc/{vmid}/vncproxy"
        
        headers = {
            "Cookie": f"PVEAuthCookie={ticket}",
            "CSRFPreventionToken": csrf_token
        }
        
        # Request a websocket-compatible proxy
        params = {
            'websocket': 1
        }
        
        print(f"Requesting VNC proxy for {vmtype}/{vmid} on node {node}...")
        proxy_response = requests.post(proxy_url, headers=headers, data=params, verify=False)
        
        if proxy_response.status_code != 200:
            print(f"VNC proxy request failed: {proxy_response.status_code}")
            print(f"Error: {proxy_response.text}")
            return None
        
        # Extract proxy data
        proxy_data = proxy_response.json()['data']
        print("VNC proxy ticket obtained successfully!")
        
        return proxy_data
    except Exception as e:
        print(f"Error: {e}")
        return None

def start_websockify_server(listen_port, target_host, target_port):
    """
    Start a websockify server to proxy WebSocket to TCP
    """
    global proxy_process
    
    # Check if target is reachable
    print(f"Testing connection to {target_host}:{target_port}...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((target_host, int(target_port)))
        s.close()
        print("Target is reachable!")
    except Exception as e:
        print(f"Warning: Could not connect to target: {e}")
        print("Continuing anyway in case the connection is just restricted...")
    
    # Start websockify process
    print(f"Starting websockify on port {listen_port} pointing to {target_host}:{target_port}...")
    
    try:
        # First check if the port is available
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', int(listen_port)))
        s.close()
        print(f"Port {listen_port} is available")
    except Exception as e:
        print(f"Port {listen_port} is not available: {e}")
        print("Stopping any existing websockify processes...")
        try:
            subprocess.run(["pkill", "-f", "websockify"], check=False)
            time.sleep(1)
        except:
            pass
    
    # Start websockify
    try:
        target = f"{target_host}:{target_port}"
        cmd = ["websockify", str(listen_port), target]
        proxy_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Register cleanup function
        atexit.register(cleanup)
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if it's still running
        if proxy_process.poll() is None:
            print(f"Websockify started with PID {proxy_process.pid}")
            return True
        else:
            stdout, stderr = proxy_process.communicate()
            print(f"Websockify failed to start: {stderr.decode()}")
            return False
    except Exception as e:
        print(f"Error starting websockify: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Direct VNC Bridge")
    parser.add_argument("--host", help="Proxmox host")
    parser.add_argument("--user", help="Proxmox user")
    parser.add_argument("--password", help="Proxmox password")
    parser.add_argument("--node", help="Proxmox node")
    parser.add_argument("--vmid", help="VM ID")
    parser.add_argument("--type", default="qemu", help="VM type (qemu or lxc)")
    parser.add_argument("--port", type=int, default=8765, help="Local port to listen on")
    parser.add_argument("--direct", action="store_true", help="Skip API and connect directly")
    parser.add_argument("--target-port", type=int, help="Target port (only with --direct)")
    
    args = parser.parse_args()
    
    # Load credentials from .env if not provided
    credentials = get_proxmox_credentials()
    
    host = args.host or credentials.get('PROXMOX_HOST')
    user = args.user or credentials.get('PROXMOX_USER')
    password = args.password or credentials.get('PROXMOX_PASSWORD')
    
    listen_port = args.port
    
    if args.direct:
        # Direct connection mode
        if not host or not args.target_port:
            print("Error: In direct mode, you must specify --host and --target-port")
            return 1
        
        print(f"Direct connection mode: {host}:{args.target_port}")
        start_websockify_server(listen_port, host, args.target_port)
        
        print("\nDirect VNC Bridge is running!")
        print(f"Connect to: ws://localhost:{listen_port}")
        print("Press Ctrl+C to stop...")
        
        try:
            # Keep the script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        
        return 0
    
    # Regular API mode - verify required parameters
    node = args.node
    vmid = args.vmid
    vmtype = args.type
    
    if not host:
        print("Error: Proxmox host not specified")
        print("Use --host or set PROXMOX_HOST in .env")
        return 1
    
    if not user:
        print("Error: Proxmox user not specified")
        print("Use --user or set PROXMOX_USER in .env")
        return 1
    
    if not password:
        print("Error: Proxmox password not specified")
        print("Use --password or set PROXMOX_PASSWORD in .env")
        return 1
    
    # If node/vmid not provided, prompt for them
    if not node:
        node = input("Enter Proxmox node name: ")
    
    if not vmid:
        vmid = input("Enter VM ID: ")
    
    # Get VNC proxy ticket
    proxy_data = get_vnc_proxy_ticket(host, user, password, node, vmid, vmtype)
    
    if not proxy_data:
        print("Failed to get VNC proxy ticket. Aborting.")
        return 1
    
    # Extract target host and port
    target_host = host  # Same host as Proxmox API
    target_port = proxy_data.get('port')
    
    if not target_port:
        print("No port specified in proxy data")
        return 1
    
    # Start websockify
    if not start_websockify_server(listen_port, target_host, target_port):
        print("Failed to start websockify server. Aborting.")
        return 1
    
    # Save ticket information to token file
    try:
        token_file = os.path.join(os.getcwd(), 'websocket_tokens.json')
        token_id = f"direct-{int(time.time())}"
        
        token_data = {
            "ticket": proxy_data.get('ticket', ''),
            "host": host,
            "port": target_port,
            "node": node,
            "vmid": vmid,
            "vmtype": vmtype,
            "created_at": time.time()
        }
        
        tokens = {}
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                try:
                    tokens = json.load(f)
                except:
                    tokens = {}
        
        tokens[token_id] = token_data
        
        with open(token_file, 'w') as f:
            json.dump(tokens, f, indent=2)
            
        print(f"Saved token information to {token_file}")
    except Exception as e:
        print(f"Warning: Could not save token information: {e}")
    
    print("\nDirect VNC Bridge is running!")
    print(f"Connect to: ws://localhost:{listen_port}")
    print("Press Ctrl+C to stop...")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
            
            # Check if websockify is still running
            if proxy_process and proxy_process.poll() is not None:
                stdout, stderr = proxy_process.communicate()
                print(f"Websockify process terminated: {stderr.decode()}")
                break
    except KeyboardInterrupt:
        print("\nStopping...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
