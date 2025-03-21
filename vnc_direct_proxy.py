#!/usr/bin/env python3
"""
Direct VNC Proxy
This script directly connects to the Proxmox API and uses its VNC proxy functionality.
"""
import os
import sys
import json
import requests
import time
import argparse

def get_proxmox_ticket(host, user, password, node, vmid, vmtype='qemu'):
    """
    Get a VNC proxy ticket directly from Proxmox API
    """
    print(f"Connecting to Proxmox API at {host}")
    
    # First, get an authentication ticket
    auth_url = f"https://{host}:8006/api2/json/access/ticket"
    auth_data = {
        "username": user,
        "password": password
    }
    
    try:
        # Disable SSL warnings - only for testing!
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        
        # Get authentication ticket
        print("Authenticating to Proxmox API...")
        auth_response = requests.post(auth_url, data=auth_data, verify=False)
        
        if auth_response.status_code != 200:
            print(f"Authentication failed: {auth_response.status_code} {auth_response.text}")
            return None
        
        auth_data = auth_response.json()['data']
        ticket = auth_data['ticket']
        csrf_token = auth_data['CSRFPreventionToken']
        
        print("✅ Authentication successful!")
        
        # Now get a VNC proxy ticket
        if vmtype == 'qemu':
            proxy_url = f"https://{host}:8006/api2/json/nodes/{node}/qemu/{vmid}/vncproxy"
        else:
            proxy_url = f"https://{host}:8006/api2/json/nodes/{node}/lxc/{vmid}/vncproxy"
        
        headers = {
            "Cookie": f"PVEAuthCookie={ticket}",
            "CSRFPreventionToken": csrf_token
        }
        
        # Request with websocket parameter set
        params = {'websocket': 1}
        
        print(f"Requesting VNC proxy for {vmtype}/{vmid} on node {node}...")
        proxy_response = requests.post(proxy_url, headers=headers, data=params, verify=False)
        
        if proxy_response.status_code != 200:
            print(f"VNC proxy request failed: {proxy_response.status_code} {proxy_response.text}")
            return None
        
        proxy_data = proxy_response.json()['data']
        print("✅ VNC proxy ticket obtained!")
        print(f"VNC proxy data: {json.dumps(proxy_data, indent=2)}")
        
        return proxy_data
    except Exception as e:
        print(f"Error connecting to Proxmox API: {e}")
        return None

def load_credentials():
    """Load Proxmox credentials from .env file"""
    credentials = {}
    
    # Try to find .env file
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    credentials[key] = value
    
    return credentials

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Get a VNC proxy ticket directly from Proxmox API")
    parser.add_argument("--host", help="Proxmox host")
    parser.add_argument("--user", help="Proxmox user")
    parser.add_argument("--password", help="Proxmox password")
    parser.add_argument("--node", help="Proxmox node")
    parser.add_argument("--vmid", help="VM ID")
    parser.add_argument("--type", default="qemu", help="VM type (qemu or lxc)")
    
    args = parser.parse_args()
    
    # Load credentials from .env if not provided
    credentials = load_credentials()
    
    host = args.host or credentials.get('PROXMOX_HOST')
    user = args.user or credentials.get('PROXMOX_USER')
    password = args.password or credentials.get('PROXMOX_PASSWORD')
    node = args.node
    vmid = args.vmid
    vmtype = args.type
    
    # If node and vmid not specified, try to get from token file
    if not node or not vmid:
        try:
            token_file = os.path.join(os.getcwd(), 'websocket_tokens.json')
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    tokens = json.load(f)
                    
                    if tokens:
                        token_id = list(tokens.keys())[0]
                        token_data = tokens[token_id]
                        
                        # Find node and vmid in token data
                        if 'data' in token_data and isinstance(token_data['data'], dict):
                            data = token_data['data']
                            node = node or data.get('node', '')
                            vmid = vmid or data.get('vmid', '')
                        else:
                            node = node or token_data.get('node', '')
                            vmid = vmid or token_data.get('vmid', '')
        except Exception as e:
            print(f"Error reading token file: {e}")
    
    # Check for required parameters
    if not host:
        print("Error: Proxmox host not specified. Use --host or set PROXMOX_HOST in .env")
        return 1
        
    if not user:
        print("Error: Proxmox user not specified. Use --user or set PROXMOX_USER in .env")
        return 1
        
    if not password:
        print("Error: Proxmox password not specified. Use --password or set PROXMOX_PASSWORD in .env")
        return 1
        
    if not node:
        print("Error: Proxmox node not specified. Use --node")
        return 1
        
    if not vmid:
        print("Error: VM ID not specified. Use --vmid")
        return 1
    
    # Get VNC proxy ticket
    proxy_data = get_proxmox_ticket(host, user, password, node, vmid, vmtype)
    
    if proxy_data:
        print("\n✅ Success! VNC proxy details:")
        print(f"  Port: {proxy_data.get('port', 'unknown')}")
        print(f"  Ticket: {proxy_data.get('ticket', 'unknown')[:20]}...")
        
        # Also output in format suitable for direct connection
        print("\nYou can now connect directly to the VNC server using:")
        print(f"  Host: {host}")
        print(f"  Port: {proxy_data.get('port')}")
        print(f"  Password: [use the ticket shown above]")
        
        # Update token file
        try:
            token_file = os.path.join(os.getcwd(), 'websocket_tokens.json')
            token_id = f"direct-{int(time.time())}"
            token_data = {
                "ticket": proxy_data.get('ticket', ''),
                "host": host,
                "port": proxy_data.get('port', ''),
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
                    except json.JSONDecodeError:
                        tokens = {}
            
            tokens[token_id] = token_data
            
            with open(token_file, 'w') as f:
                json.dump(tokens, f, indent=2)
                
            print(f"\nSaved token to {token_file}")
            print(f"Token ID: {token_id}")
        except Exception as e:
            print(f"Error saving token: {e}")
        
        return 0
    else:
        print("❌ Failed to get VNC proxy ticket")
        return 1

if __name__ == "__main__":
    sys.exit(main())
