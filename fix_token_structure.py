#!/usr/bin/env python3
"""
Fix token data structure in the token file
"""
import json
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("token-fixer")

TOKEN_FILE = os.path.abspath(os.path.join(os.getcwd(), 'websocket_tokens.json'))

def fix_token_structure():
    """Fix the token data structure"""
    if not os.path.exists(TOKEN_FILE):
        logger.error(f"Token file does not exist: {TOKEN_FILE}")
        return False
    
    try:
        # Read current tokens
        with open(TOKEN_FILE, 'r') as f:
            tokens = json.load(f)
        
        logger.info(f"Read {len(tokens)} tokens from {TOKEN_FILE}")
        
        # Create a new tokens dictionary with fixed structure
        fixed_tokens = {}
        fixed_count = 0
        
        for token_id, token_data in tokens.items():
            # Check if token has nested data structure
            if 'data' in token_data and isinstance(token_data['data'], dict):
                data = token_data['data']
                # Create a new token with flattened structure
                fixed_tokens[token_id] = {
                    'ticket': data.get('ticket', ''),
                    'host': data.get('host', ''),
                    'port': data.get('port', 0),
                    'node': data.get('node', ''),
                    'vmid': data.get('vmid', ''),
                    'vmtype': data.get('vmtype', ''),
                    'cert': data.get('cert', None),
                    'created_at': token_data.get('created_at', 0)
                }
                fixed_count += 1
                logger.info(f"Fixed nested data structure for token {token_id}")
            else:
                # Already in the correct format, just copy
                fixed_tokens[token_id] = token_data
                logger.info(f"Token {token_id} already has correct structure")
        
        # Write back the fixed tokens
        with open(TOKEN_FILE, 'w') as f:
            json.dump(fixed_tokens, f, indent=2)
        
        logger.info(f"Successfully fixed {fixed_count} tokens")
        return True
    except Exception as e:
        logger.exception(f"Error fixing token structure: {e}")
        return False

if __name__ == "__main__":
    print(f"Fixing token structure in {TOKEN_FILE}...")
    if fix_token_structure():
        print("✅ Token structure fixed successfully!")
    else:
        print("❌ Failed to fix token structure")
        sys.exit(1)
