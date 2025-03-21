#!/usr/bin/env python3
"""
Test WebSocket Connectivity
"""
import asyncio
import json
import os
import sys
import time
import websockets
import argparse

# Token file
TOKEN_FILE = os.path.join(os.getcwd(), 'websocket_tokens.json')

async def test_connection(url, timeout=5):
    """Test WebSocket connection to a URL"""
    print(f"Connecting to WebSocket: {url}")
    print(f"Timeout: {timeout} seconds")
    
    try:
        # Set a timeout for the connection attempt
        async with asyncio.timeout(timeout):
            async with websockets.connect(url) as websocket:
                print("✅ WebSocket connection established!")
                
                # Try to send a message
                test_message = json.dumps({"type": "ping", "timestamp": time.time()})
                await websocket.send(test_message)
                print(f"Sent test message: {test_message}")
                
                # Try to receive a response with timeout
                try:
                    async with asyncio.timeout(3):
                        response = await websocket.recv()
                        print(f"Received response: {response}")
                except asyncio.TimeoutError:
                    print("⚠️ No response received within timeout")
                
                # Connection was successful
                return True
    except asyncio.TimeoutError:
        print("❌ Connection attempt timed out")
        return False
    except ConnectionRefusedError:
        print("❌ Connection refused - server not running or blocking connections")
        return False
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Invalid status code: {e}")
        print("This usually means the server rejected the WebSocket upgrade request")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def get_latest_token():
    """Get the latest token from the token file"""
    try:
        if not os.path.exists(TOKEN_FILE):
            print(f"Token file does not exist: {TOKEN_FILE}")
            return None
            
        with open(TOKEN_FILE, 'r') as f:
            tokens = json.load(f)
            
        if not tokens:
            print("No tokens found in token file")
            return None
            
        # Get the most recently created token
        latest_token = None
        latest_time = 0
        
        for token_id, token_data in tokens.items():
            created_at = token_data.get('created_at', 0)
            if created_at > latest_time:
                latest_token = token_id
                latest_time = created_at
        
        if latest_token:
            print(f"Found token: {latest_token} (created {time.time() - latest_time:.1f} seconds ago)")
            return latest_token
        else:
            print("No valid token found")
            return None
    except Exception as e:
        print(f"Error reading token file: {e}")
        return None

async def main():
    parser = argparse.ArgumentParser(description="Test WebSocket connectivity")
    parser.add_argument("--host", default="localhost", help="WebSocket server host")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket server port")
    parser.add_argument("--token", help="Token to use (if not provided, will use latest from token file)")
    parser.add_argument("--path", default="/api/ws/vnc", help="WebSocket path")
    parser.add_argument("--type", default="qemu", help="VM type")
    parser.add_argument("--timeout", type=int, default=5, help="Connection timeout in seconds")
    
    args = parser.parse_args()
    
    # Get token if not provided
    token = args.token
    if not token:
        token = get_latest_token()
        if not token:
            print("No token available. Please provide a token with --token")
            return
    
    # Build the URL
    url = f"ws://{args.host}:{args.port}{args.path}?token={token}&type={args.type}"
    
    # Test the connection
    await test_connection(url, args.timeout)

if __name__ == "__main__":
    asyncio.run(main())
