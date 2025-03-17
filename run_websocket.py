#!/usr/bin/env python3
"""
WebSocket server for ProxGui VNC connections
"""
import os
import sys
import asyncio
import websockets
import logging
from urllib.parse import urlparse, parse_qs

# Add the app path to the import search path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the module with the WebSocket handling logic
from app.proxmox.websocket import handle_websocket, clean_old_connections

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('websocket.log')
    ]
)
logger = logging.getLogger("websocket-server")

async def main():
    """
    Start the WebSocket server
    """
    # Default host and port
    host = '0.0.0.0'  # Listen on all interfaces
    port = 8765       # WebSocket port
    
    # Check for environment variables
    if 'WEBSOCKET_HOST' in os.environ:
        host = os.environ['WEBSOCKET_HOST']
    if 'WEBSOCKET_PORT' in os.environ:
        port = int(os.environ['WEBSOCKET_PORT'])
    
    # Create a WebSocket server
    async with websockets.serve(handle_websocket, host, port):
        logger.info(f"WebSocket server running on {host}:{port}")
        
        # Clean up old connections periodically
        while True:
            clean_old_connections()
            await asyncio.sleep(60)  # Run every minute

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("WebSocket server stopped by user")
    except Exception as e:
        logger.error(f"WebSocket server error: {e}")
        logger.exception(e)
