#!/usr/bin/env python3
"""
Simple VNC connectivity test
"""
import socket
import sys
import time
import argparse

def test_connection(host, port, timeout=5):
    """Test direct TCP connection to a host:port"""
    print(f"Testing direct TCP connection to {host}:{port}...")
    
    try:
        # Create socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        
        # Try to connect
        start_time = time.time()
        s.connect((host, int(port)))
        elapsed = time.time() - start_time
        
        print(f"✅ Connection successful! Took {elapsed:.3f} seconds")
        
        # Try to receive data (VNC server should send a greeting)
        try:
            data = s.recv(12)
            print(f"Received: {data}")
            
            if data.startswith(b'RFB '):
                print("✅ This appears to be a VNC server (received RFB protocol header)")
            else:
                print("⚠️ Connected, but didn't receive VNC protocol header")
                print(f"First bytes: {data!r}")
        except socket.timeout:
            print("Connection established but no data received (timeout waiting for server greeting)")
        
        return True
    except ConnectionRefusedError:
        print(f"❌ Connection refused to {host}:{port}")
        print("   This usually means the port is not open or not accepting connections")
        return False
    except socket.timeout:
        print(f"❌ Connection timed out after {timeout} seconds")
        print("   This could mean the port is firewalled or the server is not responding")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    finally:
        s.close()

def main():
    parser = argparse.ArgumentParser(description="Test direct TCP connection to a host:port")
    parser.add_argument("host", help="Host to connect to")
    parser.add_argument("port", type=int, help="Port to connect to")
    parser.add_argument("--timeout", type=int, default=5, help="Connection timeout in seconds")
    
    args = parser.parse_args()
    
    test_connection(args.host, args.port, args.timeout)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python connect_test.py <host> <port> [--timeout <seconds>]")
        sys.exit(1)
    
    main()
