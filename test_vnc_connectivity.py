#!/usr/bin/env python3
"""
Test direct TCP connectivity to Proxmox VNC port
"""
import argparse
import json
import logging
import socket
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('vnc_connectivity.log')
    ]
)
logger = logging.getLogger("vnc-connectivity")

def test_connection(host, port, timeout=5):
    """Test TCP connection to a host:port"""
    logger.info(f"Testing connection to {host}:{port}...")
    
    try:
        # Create socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        
        # Record start time
        start = time.time()
        
        # Try to connect
        s.connect((host, int(port)))
        
        # Calculate elapsed time
        elapsed = time.time() - start
        
        logger.info(f"Connection successful! Time: {elapsed:.3f} seconds")
        print(f"✅ Successfully connected to {host}:{port} in {elapsed:.3f} seconds")
        
        # Try to receive initial VNC greeting
        try:
            greeting = s.recv(12)
            greeting_str = greeting.decode('ascii', errors='replace')
            logger.info(f"Received greeting: {greeting_str}")
            print(f"Received greeting: {greeting_str}")
            
            if greeting.startswith(b'RFB '):
                print("✅ Valid VNC server greeting received!")
            else:
                print("⚠️ Connected but received unexpected data (not VNC protocol)")
                
        except socket.timeout:
            logger.warning("Connected but timeout waiting for greeting")
            print("⚠️ Connected but timeout waiting for greeting")
        
        return True
    except socket.timeout:
        logger.error(f"Connection timed out after {timeout} seconds")
        print(f"❌ Connection timed out after {timeout} seconds")
        return False
    except ConnectionRefusedError:
        logger.error("Connection refused")
        print(f"❌ Connection refused to {host}:{port}")
        return False
    except Exception as e:
        logger.exception(f"Connection error: {e}")
        print(f"❌ Connection failed: {e}")
        return False
    finally:
        try:
            s.close()
        except:
            pass

def get_token_data(token_file='websocket_tokens.json'):
    """Get all token data from file"""
    try:
        with open(token_file, 'r') as f:
            tokens = json.load(f)
            return tokens
    except Exception as e:
        logger.exception(f"Error loading tokens: {e}")
        return {}

def test_all_tokens(token_file='websocket_tokens.json'):
    """Test connectivity for all tokens in the token file"""
    tokens = get_token_data(token_file)
    
    if not tokens:
        print(f"No tokens found in {token_file}")
        return
    
    print(f"Found {len(tokens)} token(s) to test")
    
    for token_id, token_data in tokens.items():
        print(f"\nTesting token: {token_id}")
        
        # Get host and port - handle both old and new token structures
        if 'data' in token_data and isinstance(token_data['data'], dict):
            # Old structure
            data = token_data['data']
            host = data.get('host', '')
            port = data.get('port', 0)
        else:
            # New structure
            host = token_data.get('host', '')
            port = token_data.get('port', 0)
        
        if not host or not port:
            print(f"❌ Invalid token data - missing host or port: {token_data}")
            continue
        
        test_connection(host, port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test VNC connectivity")
    parser.add_argument("--host", help="Host to test")
    parser.add_argument("--port", help="Port to test")
    parser.add_argument("--all-tokens", action="store_true", help="Test all tokens in file")
    parser.add_argument("--file", default="websocket_tokens.json", help="Token file path")
    
    args = parser.parse_args()
    
    if args.all_tokens:
        test_all_tokens(args.file)
    elif args.host and args.port:
        test_connection(args.host, args.port)
    else:
        parser.print_help()
