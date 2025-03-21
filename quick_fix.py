#!/usr/bin/env python3
"""
Quick fix for the nested token data structure issue
"""
import json
import os

# Path to token file
token_file = os.path.abspath(os.path.join(os.getcwd(), 'websocket_tokens.json'))

print(f"Fixing token file at: {token_file}")

if not os.path.exists(token_file):
    print("Token file does not exist. Creating empty file.")
    with open(token_file, 'w') as f:
        json.dump({}, f)
    exit(0)

# Load current tokens
try:
    with open(token_file, 'r') as f:
        tokens = json.load(f)
    
    print(f"Found {len(tokens)} tokens in file")
    
    # Process each token
    for token_id, token_data in tokens.items():
        print(f"Processing token: {token_id}")
        
        # Check if we have a nested data structure
        if 'data' in token_data and isinstance(token_data['data'], dict):
            data = token_data['data']
            # Extract all data fields to the top level
            tokens[token_id] = {
                'host': data.get('host', ''),
                'port': data.get('port', ''),
                'ticket': data.get('ticket', ''),
                'node': data.get('node', ''),
                'vmid': data.get('vmid', ''),
                'vmtype': data.get('vmtype', ''),
                'cert': data.get('cert'),
                'created_at': token_data.get('created_at', 0)
            }
            print(f"Fixed nested data structure for token: {token_id}")
    
    # Write the fixed tokens back to the file
    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)
    
    print("Token file updated successfully!")
except Exception as e:
    print(f"Error: {str(e)}")
    print("Creating clean token file...")
    
    with open(token_file, 'w') as f:
        json.dump({}, f, indent=2)
    
    print("Created clean token file. Please try again.")
