#!/usr/bin/env python3
"""
WebSocket to TCP proxy for VNC connections using Websockify

This script handles WebSocket connections and proxies them to Proxmox VNC servers
using tokens for authentication.
"""
import os
import sys
import json
import time
import logging
import threading
import websockify.websocketproxy
from urllib.parse import parse_qs
import socket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('websockify.log')
    ]
)
logger = logging.getLogger("websockify-proxy")

# Constants
TOKEN_FILE = os.path.abspath(os.path.join(os.getcwd(), 'websocket_tokens.json'))

class ProxmoxTokenPlugin(object):
    """Proxmox token authentication plugin for websockify"""
    
    def __init__(self, src=None):
        self.source = src
        logger.info(f"Token plugin initialized with source: {src}")
        logger.info(f"Using token file: {TOKEN_FILE}")
    
    def lookup(self, token):
        """Look up a token and return host:port for the connection target"""
        logger.info(f"Looking up token: {token}")
        
        try:
            if not os.path.exists(TOKEN_FILE):
                logger.error(f"Token file does not exist: {TOKEN_FILE}")
                return None
            
            with open(TOKEN_FILE, 'r') as f:
                try:
                    tokens = json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing token file: {e}")
                    return None
                
                logger.info(f"Token file contains {len(tokens)} tokens")
                
                if token not in tokens:
                    logger.warning(f"Token not found: {token}")
                    return None
                
                token_data = tokens[token]
                logger.info(f"Found token data: {token_data}")
                
                # Extract connection information - handle both formats
                # Format 1: {'host': '...', 'port': '...'}
                # Format 2: {'data': {'host': '...', 'port': '...'}}
                host = token_data.get('host', '')
                port = token_data.get('port', 0)
                
                # Check if we're dealing with the nested format
                if not host and 'data' in token_data and isinstance(token_data['data'], dict):
                    data = token_data['data']
                    host = data.get('host', '')
                    port = data.get('port', 0)
                    logger.info(f"Using nested data format: host={host}, port={port}")
                
                if not host or not port:
                    logger.error(f"Token missing host or port: {token_data}")
                    return None
                
                # Return connection target
                connection = f"{host}:{port}"
                logger.info(f"Returning connection target: {connection}")
                # Explicitly try connecting to confirm it's reachable
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    logger.info(f"Testing direct connection to {host}:{port}...")
                    sock.connect((host, int(port)))
                    logger.info(f"Successfully connected to {host}:{port}")
                    sock.close()
                except Exception as e:
                    logger.warning(f"Could not establish direct connection to {host}:{port}: {e}")
                return connection
        except Exception as e:
            logger.exception(f"Error looking up token: {e}")
            return None

class ProxmoxWebsockifyServer(websockify.websocketproxy.WebSocketProxy):
    """Custom websockify server for Proxmox VNC connections"""
    
    def new_client(self):
        """Called when a new WebSocket client connects"""
        try:
            # Parse query string to get token and type
            if hasattr(self, 'path') and self.path:
                query = parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
                token = query.get('token', [''])[0]
                vmtype = query.get('type', ['qemu'])[0]
                
                logger.info(f"New connection with token: {token}, type: {vmtype}")
                
                # Continue with normal websockify connection handling
                super(ProxmoxWebsockifyServer, self).new_client()
            else:
                logger.error("No path information available")
                raise Exception("Missing path information")
        except Exception as e:
            logger.exception(f"Error in new_client: {e}")
            raise

def main():
    """Run the websockify proxy server"""
    logger.info(f"Starting websockify proxy server")
    
    host = os.environ.get('WEBSOCKET_HOST', '0.0.0.0')
    port = int(os.environ.get('WEBSOCKET_PORT', 8765))
    
    # Configure the server
    server = ProxmoxWebsockifyServer(
        listen_host=host,
        listen_port=port,
        token_plugin=ProxmoxTokenPlugin(src=TOKEN_FILE),
        daemon=False,
        ssl_only=False,
        web=None,
        target_host='ignore',
        target_port='ignore'
    )
    
    logger.info(f"Server configured on {host}:{port}")
    
    # Run the server
    try:
        server.start_server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"Server error: {e}")

if __name__ == "__main__":
    main()
