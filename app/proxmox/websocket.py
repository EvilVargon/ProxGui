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
from app.proxmox.token_store import get_token, cleanup_tokens, TOKEN_FILE

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
        logger.info(f"Using token file: {TOKEN_FILE}")
        logger.info(f"Token file exists: {os.path.exists(TOKEN_FILE)}")
        
        # Try to display the contents of the token file for debugging
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    file_content = f.read()
                    logger.info(f"Token file contents: {file_content[:1000]}")
        except Exception as e:
            logger.error(f"Error reading token file: {e}")
        
        # Validate token
        if not token:
            logger.warning(f"Client from {client_address} tried to connect without token")
            self.close(1008, "Missing token")
            return
        
        # Get token data from the centralized token store
        token_data = get_token(token)
        logger.info(f"Token data retrieved: {token_data is not None}")
        
        if token_data:
            logger.info(f"Token validated successfully: {token}")
            
            # Use token data directly without expecting a nested 'data' field
            actual_data = token_data
            
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
                
                # *** Implement a basic VNC proxy for debugging ***
                # In a production environment, you should implement a proper VNC proxy
                # with a library like websockify
                
                # For now, we'll implement a simple echo proxy that simulates a VNC connection
                # This won't work with a real VNC client but will help debug the connection flow
                
                # Send a welcome message
                self.send_message(json.dumps({
                    "type": "vnc.connected", 
                    "message": "VNC connection established successfully",
                    "ticket": actual_data.get('ticket', 'unknown')
                }))
                
                # Here's where you would normally connect to the Proxmox VNC server
                # using the ticket, but we're just simulating it for debugging purposes
                #
                # Steps for a real implementation would be:
                # 1. Connect to the Proxmox VNC server using the ticket
                # 2. Set up a proxy to forward data between the WebSocket and the VNC server
                # 3. Handle disconnections properly
                #
                # For a complete implementation, you might want to use websockify or
                # implement a direct TCP-to-WebSocket proxy
                
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