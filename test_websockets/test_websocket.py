#!/usr/bin/env python3
import asyncio
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def echo(websocket):
    logger.info(f"New connection from {websocket.remote_address}, path: {websocket.path}")
    try:
        async for message in websocket:
            logger.info(f"Received message: {message[:50]}...")
            await websocket.send(f"Echo: {message}")
    except Exception as e:
        logger.exception(f"Error in WebSocket connection: {e}")
    finally:
        logger.info(f"Connection from {websocket.remote_address} closed")

async def main():
    # Start a WebSocket server
    host = "127.0.0.1"
    port = 8765
    
    logger.info(f"Starting WebSocket echo server on {host}:{port}")
    async with websockets.serve(echo, host, port):
        # Keep the server running indefinitely
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")