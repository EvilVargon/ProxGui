#!/usr/bin/env python3
"""
Direct VNC connection test - bypasses websockify
"""
import socket
import sys
import time
import json
import os

def test_connection(host, port, timeout=5):
    """Test direct TCP connection"""
    print(f"Testing direct connection to {host}:{port}...")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    
    try:
        start = time.time()
        s.connect((host, int(port)))
        elapsed = time.time() - start
        
        print(f"SUCCESS: Connected to {host}:{port} in {elapsed:.2f} seconds")
        
        # Try reading the VNC header
        try:
            header = s.recv(12)
            print(f"Received: {header}")
            if header.startswith(b'RFB '):
                print("✅ This appears to be a valid VNC server")
            else:
                print("⚠️ Connected but didn't receive expected VNC header")
        except socket.timeout:
            print("Received no data (timeout reading)")
        
        return True
    except Exception as e:
        print(f"FAILED: Could not connect to {host}:{port} - {e}")
        return False
    finally:
        s.close()

def get_host_port_from_token_file():
    """Extract host and port from the token file"""
    token_file = os.path.join(os.getcwd(), 'websocket_tokens.json')
    
    if not os.path.exists(token_file):
        print(f"Token file not found: {token_file}")
        return None, None
    
    try:
        with open(token_file, 'r') as f:
            tokens = json.load(f)
            
        if not tokens:
            print("No tokens found in token file")
            return None, None
            
        # Get the first token's data
        token_id = list(tokens.keys())[0]
        token_data = tokens[token_id]
        
        # Check for nested data
        if 'data' in token_data and isinstance(token_data['data'], dict):
            data = token_data['data']
            host = data.get('host', '')
            port = data.get('port', '')
        else:
            host = token_data.get('host', '')
            port = token_data.get('port', '')
        
        print(f"Found host:{host} port:{port} in token file")
        return host, port
    except Exception as e:
        print(f"Error reading token file: {e}")
        return None, None

if __name__ == "__main__":
    # Parse command line args
    if len(sys.argv) == 3:
        host = sys.argv[1]
        port = sys.argv[2]
    else:
        # Try to get from token file
        host, port = get_host_port_from_token_file()
        
        if not host or not port:
            print("Usage: python direct_test.py <host> <port>")
            sys.exit(1)
    
    # Try the connection
    test_connection(host, port)
