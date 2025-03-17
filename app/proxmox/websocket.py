#!/usr/bin/env python3
"""
WebSocket handler for VNC connections
"""
import asyncio
import json
import logging
import secrets
import time
import websockets
import ssl
from urllib.parse import parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket-handler")

import uuid

# Store active VNC connections
active_connections = {}
connection_tokens = {}

def generate_token():
    """
    Generate a unique token for VNC connections
    """
    return str(uuid.uuid4())

def store_vnc_connection(token, vnc_info, host, port, verify_ssl=True):
    """
    Store VNC connection details for websocket proxy
    """
    connection_tokens[token] = {
        'host': host,
        'port': port,
        'ticket': vnc_info.get('ticket'),
        'vnc_info': vnc_info,
        'created_at': time.time(),
        'verify_ssl': verify_ssl
    }
    logger.info(f"Stored VNC connection with token {token}")
    return token

async def handle_websocket(websocket, path):
    """
    Handle WebSocket connections for VNC
    """
    query = parse_qs(path.split('?', 1)[1]) if '?' in path else {}
    token = query.get('token', [None])[0]
    vmtype = query.get('type', [None])[0]
    
    # Log connection details
    client_host = websocket.remote_address[0] if hasattr(websocket, 'remote_address') else 'unknown'
    logger.info(f"New WebSocket connection from {client_host} for path {path}")
    
    if token is None:
        logger.warning(f"Client from {client_host} tried to connect without token")
        await websocket.close(1008, "Missing token")
        return
    
    # Validate token
    if token not in connection_tokens:
        logger.warning(f"Client from {client_host} tried to connect with invalid token")
        await websocket.close(1008, "Invalid token")
        return
    
    vnc_info = connection_tokens[token]
    logger.info(f"Validated token for {vmtype} VM with host {vnc_info['host']}:{vnc_info['port']}")
    
    # Connect to the VNC server
    try:
        # Register this connection
        conn_id = secrets.token_hex(16)
        active_connections[conn_id] = {
            'client': websocket,
            'last_activity': time.time(),
            'vnc_info': vnc_info,
            'client_host': client_host
        }
        
        # Simple heartbeat to keep connection alive
        while True:
            try:
                message = await websocket.recv()
                # In a real implementation, you would forward this to the VNC server
                # For now we'll just acknowledge messages
                await websocket.send(json.dumps({
                    "type": "ack",
                    "message": "Message received"
                }))
                
                # Update last activity
                active_connections[conn_id]['last_activity'] = time.time()
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Connection from {client_host} closed")
                break
            except Exception as e:
                logger.exception(f"Error handling websocket message: {e}")
                break
    except Exception as e:
        logger.exception(f"Error handling websocket: {e}")
    finally:
        # Clean up connection
        if conn_id in active_connections:
            del active_connections[conn_id]
        logger.info(f"Connection from {client_host} closed, removed from active connections")

def register_vnc_connection(token, host, port, ticket):
    """
    Register a new VNC connection
    """
    connection_tokens[token] = {
        'host': host,
        'port': port,
        'ticket': ticket,
        'created_at': time.time()
    }
    logger.info(f"Registered new VNC connection to {host}:{port} with token {token}")
    return token

def clean_old_connections():
    """
    Clean up expired connections
    """
    current_time = time.time()
    expired_tokens = []
    
    # Find expired tokens (older than 5 minutes)
    for token, info in connection_tokens.items():
        if current_time - info['created_at'] > 300:  # 5 minutes
            expired_tokens.append(token)
    
    # Remove expired tokens
    for token in expired_tokens:
        if token in connection_tokens:
            del connection_tokens[token]
    
    # Find and close inactive connections (no activity for 5 minutes)
    inactive_connections = []
    for conn_id, conn_info in active_connections.items():
        if current_time - conn_info['last_activity'] > 300:  # 5 minutes
            inactive_connections.append(conn_id)
    
    # Log results
    if expired_tokens or inactive_connections:
        logger.info(f"Cleaned up {len(expired_tokens)} expired tokens and {len(inactive_connections)} inactive connections")
    
    return len(expired_tokens) + len(inactive_connections)
