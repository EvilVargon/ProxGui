#!/usr/bin/env python3
from simple_websocket_server import WebSocketServer, WebSocket
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleEcho(WebSocket):
    def handle(self):
        # Echo message back to client
        logger.info(f"Received: {self.data}")
        self.send_message(f"Echo: {self.data}")

    def connected(self):
        logger.info(f"Connected: {self.address}")

    def handle_close(self):
        logger.info(f"Closed: {self.address}")

if __name__ == "__main__":
    host = '127.0.0.1'
    port = 8765
    
    logger.info(f"Starting simple WebSocket server on {host}:{port}")
    server = WebSocketServer(host, port, SimpleEcho)
    server.serve_forever()