#!/usr/bin/env python3
"""
Debug WebSocket server for VNC connections
"""
import json
import logging
import os
import threading
import time
import uuid
from simple_websocket_server import WebSocketServer, WebSocket
from urllib.parse import parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_websocket.log')
    ]
)
logger = logging.getLogger("debug-websocket")

# File to store tokens
TOKEN_FILE = 'debug_tokens.json'
DEBUG_TOKEN = str(uuid.uuid4())  # Generate a fixed token for testing

# Create a debug token and save it
with open(TOKEN_FILE, 'w') as f:
    token_data = {
        DEBUG_TOKEN: {
            'host': 'localhost',
            'port': 8006,
            'ticket': 'debug-ticket',
            'created_at': time.time()
        }
    }
    json.dump(token_data, f)
    logger.info(f"Created debug token: {DEBUG_TOKEN}")

def load_tokens():
    """Load tokens from file"""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
                logger.info(f"Loaded {len(tokens)} tokens from file")
                return tokens
        logger.warning(f"Token file {TOKEN_FILE} not found")
        return {}
    except Exception as e:
        logger.exception(f"Error loading tokens: {e}")
        return {}

class DebugWebSocketHandler(WebSocket):
    def handle(self):
        """Handle incoming WebSocket messages"""
        try:
            logger.info(f"Received message: {self.data[:50]}...")
            self.send_message(json.dumps({
                "type": "debug-echo",
                "message": f"Echo: {self.data}"
            }))
        except Exception as e:
            logger.exception(f"Error handling message: {e}")

    def connected(self):
        """Handle new WebSocket connection"""
        client_address = self.address[0] if hasattr(self, 'address') else 'unknown'
        logger.info(f"New connection from {client_address}")
        
        # Parse path and query string
        path = self.request.path if hasattr(self.request, 'path') else ''
        logger.info(f"Connection path: {path}")
        
        # Extract the query string and parse it
        query = {}
        try:
            if '?' in path:
                query_string = path.split('?', 1)[1]
                logger.info(f"Query string: {query_string}")
                
                # Parse the query string manually for debugging
                query_parts = query_string.split('&')
                for part in query_parts:
                    if '=' in part:
                        key, value = part.split('=', 1)
                        query[key] = value
                        logger.info(f"Parsed query param: {key}={value}")
        except Exception as e:
            logger.exception(f"Error parsing query string: {e}")
        
        # Get token from query
        token = query.get('token', '')
        logger.info(f"Token from query: {token}")
        
        # Load tokens
        tokens = load_tokens()
        logger.info(f"Available tokens: {list(tokens.keys())}")
        
        # Validate token
        if not token:
            logger.warning("Missing token")
            self.close(1008, "Missing token")
            return
            
        if token not in tokens:
            logger.warning(f"Invalid token: {token}")
            self.close(1008, "Invalid token")
            return
        
        logger.info(f"Valid token: {token}")
        logger.info("WebSocket connection established successfully")

    def handle_close(self):
        """Handle WebSocket connection close"""
        logger.info("Connection closed")

def main():
    host = '0.0.0.0'
    port = 8765
    
    logger.info(f"Starting debug WebSocket server on {host}:{port}")
    logger.info(f"Debug token: {DEBUG_TOKEN}")
    
    server = WebSocketServer(host, port, DebugWebSocketHandler)
    server.serve_forever()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"Server error: {e}")