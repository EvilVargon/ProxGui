#!/usr/bin/env python3
"""
WebSocket VNC proxy for Proxmox User Portal
"""
import asyncio
import websockets
import socket
import ssl
import json
import logging
import os
import time
import uuid
from urllib.parse import parse_qs
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('websockify.log')
    ]
)
logger = logging.getLogger("websockify")

# Token store - path to the shared token file
TOKEN_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'websocket_tokens.json'))

def load_tokens():
    """Load tokens from the shared token file"""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.exception(f"Error loading tokens: {e}")
        return {}

class VNCProxy:
    """Handle VNC proxy connections"""
    def __init__(self, host, port, token_data, ssl_verify=False):
        self.host = host
        self.port = port
        self.token_data = token_data
        self.ssl_verify = ssl_verify
        self.buffer_size = 8192
        
    async def create_connection(self):
        """Create connection to VNC server"""
        try:
            # For non-SSL connections
            if not self.ssl_verify:
                logger.info(f"Connecting to VNC server at {self.host}:{self.port}")
                reader, writer = await asyncio.open_connection(self.host, self.port)
                return reader, writer
            else:
                # For SSL connections
                context = ssl.create_default_context()
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
                
                logger.info(f"Connecting to VNC server at {self.host}:{self.port} with SSL")
                reader, writer = await asyncio.open_connection(
                    self.host, self.port, ssl=context
                )
                return reader, writer
        except Exception as e:
            logger.exception(f"Error connecting to VNC server: {str(e)}")
            raise

    async def proxy(self, websocket):
        """Proxy traffic between WebSocket and VNC server"""
        try:
            # Establish connection to VNC server
            vnc_reader, vnc_writer = await self.create_connection()
            logger.info("Connected to VNC server successfully")
            
            # Send authentication with the token/ticket
            if 'ticket' in self.token_data:
                vnc_ticket = self.token_data['ticket']
                logger.info(f"Using VNC ticket: {vnc_ticket[:10]}...")
                # This part depends on Proxmox's specific VNC authentication method
                # You may need to adjust based on what Proxmox expects
            
            # Set up bidirectional proxying
            async def ws_to_vnc():
                try:
                    async for message in websocket:
                        if isinstance(message, bytes):
                            vnc_writer.write(message)
                            await vnc_writer.drain()
                        else:
                            # Handle text frames - convert to bytes if needed
                            vnc_writer.write(message.encode('utf-8'))
                            await vnc_writer.drain()
                except Exception as e:
                    logger.exception(f"Error in websocket → VNC: {str(e)}")
                finally:
                    vnc_writer.close()
                    try:
                        await vnc_writer.wait_closed()
                    except:
                        pass
            
            async def vnc_to_ws():
                try:
                    while True:
                        data = await vnc_reader.read(self.buffer_size)
                        if not data:
                            break
                        await websocket.send(data)
                except Exception as e:
                    logger.exception(f"Error in VNC → websocket: {str(e)}")
                finally:
                    try:
                        await websocket.close()
                    except:
                        pass
            
            # Run both directions concurrently
            await asyncio.gather(
                ws_to_vnc(),
                vnc_to_ws()
            )
        except Exception as e:
            logger.exception(f"Error in VNC proxy: {str(e)}")
            await websocket.close(1011, f"Error connecting to VNC server: {str(e)}")

async def handle_websocket(websocket, path):
    """Handle incoming WebSocket connections"""
    try:
        # Log connection
        client_address = websocket.remote_address if hasattr(websocket, 'remote_address') else 'unknown'
        logger.info(f"New connection from {client_address}, path: {path}")
        
        # Parse query parameters from path
        query = {}
        if '?' in path:
            query_string = path.split('?', 1)[1]
            logger.info(f"Query string: {query_string}")
            parts = query_string.split('&')
            for part in parts:
                if '=' in part:
                    k, v = part.split('=', 1)
                    query[k] = v
        
        # Get token from query
        token = query.get('token', '')
        logger.info(f"Token: {token}")
        
        if not token:
            logger.warning("No token provided")
            await websocket.close(1008, "No token provided")
            return
        
        # Load and validate token
        tokens = load_tokens()
        logger.info(f"Available tokens: {list(tokens.keys())}")
        
        if token not in tokens:
            logger.warning(f"Invalid token: {token}")
            await websocket.close(1008, "Invalid token")
            return
        
        # Extract token data - handle both formats
        token_data = tokens[token].get('data', tokens[token])
        if not token_data:
            logger.warning(f"Invalid token data for token: {token}")
            await websocket.close(1008, "Invalid token data")
            return
        
        # Get connection details
        host = token_data.get('host')
        port = token_data.get('port', 5900)  # Default VNC port
        
        if not host:
            logger.warning("No host in token data")
            await websocket.close(1008, "No host specified in token data")
            return
        
        logger.info(f"Valid token for {host}:{port}")
        
        # Create and start proxy
        proxy = VNCProxy(host, port, token_data)
        await proxy.proxy(websocket)
    except Exception as e:
        logger.exception(f"Error in websocket handler: {str(e)}")
        try:
            await websocket.close(1011, f"Error: {str(e)}")
        except:
            pass

async def main():
    # Start the WebSocket server
    host = os.environ.get('WEBSOCKET_HOST', '0.0.0.0')
    port = int(os.environ.get('WEBSOCKET_PORT', 8765))
    
    logger.info(f"Starting WebSocket proxy server on {host}:{port}")
    async with websockets.serve(handle_websocket, host, port):
        # Keep the server running indefinitely
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("WebSocket proxy server stopped by user")
    except Exception as e:
        logger.exception(f"WebSocket server error: {e}")
