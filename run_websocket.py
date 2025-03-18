#!/usr/bin/env python3
"""
WebSocket server for ProxGui VNC connections
"""
import os
import sys
import logging

# Add the app path to the import search path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the module with the WebSocket handling logic
from app.proxmox.websocket import start_websocket_server, stop_websocket_server

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
    try:
        # Get host and port from environment variables if set
        host = os.environ.get('WEBSOCKET_HOST', '0.0.0.0')
        port = int(os.environ.get('WEBSOCKET_PORT', 8765))
        
        # Start the WebSocket server
        server = start_websocket_server(host, port)
        logger.info(f"WebSocket server running on {host}:{port}")
        
        # Keep the main thread alive
        import asyncio
        await asyncio.Future()  # Run forever
            
    except Exception as e:
        logger.error(f"WebSocket server error: {e}")
        logger.exception(e)

if __name__ == "__main__":
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("WebSocket server stopped by user")
        stop_websocket_server()
    except Exception as e:
        logger.error(f"WebSocket server error: {e}")
        logger.exception(e)