#!/usr/bin/env python3
"""
WebSocket handler for VNC connections using simple-websocket-server
"""
import json
import logging
import secrets
import time
import threading
import uuid
from urllib.parse import parse_qs
from simple_websocket_server import WebSocketServer, WebSocket

# Import token storage - use the single consistent token store
from app.proxmox.token_store import get_token, cleanup_tokens

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket-handler")

# Store active VNC connections (runtime connections, not persistent storage)
active_connections = {}

def generate_token():
    """
    Generate a unique token for VNC connections
    """
    return str(uuid.uuid4())

class VNCWebSocketHandler(WebSocket):
    def handle(self):
        """Handle incoming WebSocket messages"""
        try:
            # Forward the message (in a real implementation)
            logger.info(f"Received message from client: {self.data[:50]}...")
            
            # Just acknowledge messages for now
            self.send_message(json.dumps({
                "type": "ack",
                "message": "Message received"
            }))
            
            # Update last activity for this connection
            if hasattr(self, 'conn_id') and self.conn_id in active_connections:
                active_connections[self.conn_id]['last_activity'] = time.time()
                
        except Exception as e:
            logger.exception(f"Error handling message: {e}")
    
    def connected(self):
        """Handle new WebSocket connection"""
        client_address = self.address[0] if hasattr(self, 'address') else 'unknown'
        logger.info(f"New WebSocket connection from {client_address}")
        
        # Parse query parameters from path
        path = self.request.path if hasattr(self.request, 'path') else ''
        logger.info(f"Connection path: {path}")
        
        # Parse query parameters more robustly
        try:
            query = {}
            if '?' in path:
                query_string = path.split('?', 1)[1]
                logger.info(f"Query string: {query_string}")
                
                parts = query_string.split('&')
                for part in parts:
                    if '=' in part:
                        k, v = part.split('=', 1)
                        query[k] = v
                        logger.info(f"Parsed query param: {k}={v}")
        except Exception as e:
            logger.exception(f"Error parsing query string: {e}")
            query = {}
        
        token = query.get('token', '')
        vmtype = query.get('type', '')
        
        logger.info(f"Token from query: {token}")
        
        # Validate token
        if not token:
            logger.warning(f"Client from {client_address} tried to connect without token")
            self.close(1008, "Missing token")
            return
        
        # Get token data from the centralized token store
        token_data = get_token(token)
        
        if token_data:
            # Handle the token data format
            actual_data = token_data.get('data', {})
            logger.info(f"Token validated successfully: {token}")
            
            # *** DEBUG: Print the token data to see what we have ***
            logger.info(f"Token data: {actual_data}")
            
            try:
                # For debugging only - accept the connection and echo data
                # In a real implementation, establish actual VNC connection
                
                # Register this connection
                self.conn_id = secrets.token_hex(16)
                active_connections[self.conn_id] = {
                    'client': self,
                    'last_activity': time.time(),
                    'token_data': actual_data,
                    'client_host': client_address
                }
                
                logger.info(f"Connection {self.conn_id} registered successfully")
                
                # *** This is a stub for actual VNC proxy implementation ***
                # You'll need to implement the actual VNC proxy connection
                # using a library like websockify or vnc-websocket-proxy
                
                # For now, just accept the connection and echo data
                # Send a welcome message
                self.send_message(json.dumps({
                    "type": "success", 
                    "message": "WebSocket connection established successfully"
                }))
                
            except Exception as e:
                logger.exception(f"Error establishing VNC connection: {e}")
                self.close(1011, f"Failed to establish VNC connection: {str(e)}")
        else:
            logger.warning(f"Invalid token: {token}")
            self.close(1008, "Invalid token")

    def handle_close(self):
        """Handle WebSocket connection close"""
        client_address = self.address[0] if hasattr(self, 'address') else 'unknown'
        logger.info(f"Connection from {client_address} closed")
        
        # Remove from active connections
        if hasattr(self, 'conn_id') and self.conn_id in active_connections:
            del active_connections[self.conn_id]
            logger.info(f"Connection {self.conn_id} removed from active connections")

# Global server instance
server = None
server_thread = None

def start_websocket_server(host='0.0.0.0', port=8765):
    """Start the WebSocket server in a background thread"""
    global server, server_thread
    
    # Create and start the server
    logger.info(f"Starting WebSocket server on {host}:{port}")
    server = WebSocketServer(host, port, VNCWebSocketHandler)
    
    # Run server in a separate thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Start a cleanup thread
    def cleanup_thread():
        while True:
            try:
                cleanup_tokens()
                time.sleep(60)  # Run every minute
            except Exception as e:
                logger.exception(f"Error in cleanup thread: {e}")
    
    cleanup = threading.Thread(target=cleanup_thread)
    cleanup.daemon = True
    cleanup.start()
    
    return server

def stop_websocket_server():
    """Stop the WebSocket server"""
    global server
    if server:
        logger.info("Stopping WebSocket server")
        server.close()
        server = None