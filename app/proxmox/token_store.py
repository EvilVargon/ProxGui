# app/proxmox/token_store.py
import os
import json
import time
import threading
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Use absolute path for token file
# Make sure this is an absolute path to avoid any path resolution issues
TOKEN_FILE = os.path.abspath(os.path.join(os.getcwd(), 'websocket_tokens.json'))
TOKEN_LOCK = threading.Lock()

# Ensure token file exists with proper structure on module import
def initialize_token_file():
    """Ensure token file exists and is properly initialized"""
    if not os.path.exists(TOKEN_FILE):
        logger.info(f"Creating new token file at {TOKEN_FILE}")
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            json.dump({}, f)
    else:
        # Verify the file contains valid JSON
        try:
            with open(TOKEN_FILE, 'r') as f:
                content = f.read().strip()
                if not content:  # Empty file
                    logger.info(f"Empty token file found, initializing with empty object")
                    with open(TOKEN_FILE, 'w') as f:
                        json.dump({}, f)
                else:
                    json.loads(content)  # Just to validate
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in token file, reinitializing")
            with open(TOKEN_FILE, 'w') as f:
                json.dump({}, f)

# Initialize token file when module is imported
initialize_token_file()

def save_token(token, data):
    """Save a token to the shared file"""
    logger.info(f"Saving token {token} to file {TOKEN_FILE}")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    
    with TOKEN_LOCK:
        # Load existing tokens
        tokens = {}
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    content = f.read().strip()
                    if content:
                        tokens = json.loads(content)
                    else:
                        tokens = {}
            except json.JSONDecodeError:
                # If file is corrupted, start fresh
                tokens = {}
        
        # Add the new token
        tokens[token] = {
            'data': data,
            'created_at': time.time()
        }
        
        # Save back to file
        with open(TOKEN_FILE, 'w') as f:
            json.dump(tokens, f)
        
        logger.info(f"Saved token {token} to file {TOKEN_FILE}")
        logger.debug(f"File now contains {len(tokens)} tokens")
    
    return True

def get_token(token):
    """Get a token from the shared file"""
    logger.debug(f"Looking up token {token} in file {TOKEN_FILE}")
    
    if not os.path.exists(TOKEN_FILE):
        logger.warning(f"Token file {TOKEN_FILE} does not exist")
        return None
    
    with TOKEN_LOCK:
        try:
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
                if token in tokens:
                    logger.debug(f"Found token {token} in file")
                    return tokens[token]
                else:
                    logger.warning(f"Token {token} not found in file")
                    logger.debug(f"Available tokens: {list(tokens.keys())}")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error reading token file: {e}")
            return None
    
    return None

def cleanup_tokens():
    """Remove expired tokens (older than 5 minutes)"""
    if not os.path.exists(TOKEN_FILE):
        return 0
    
    with TOKEN_LOCK:
        try:
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
            
            current_time = time.time()
            expired = []
            
            for token, data in tokens.items():
                if current_time - data.get('created_at', 0) > 300:  # 5 minutes
                    expired.append(token)
            
            if expired:
                for token in expired:
                    del tokens[token]
                
                with open(TOKEN_FILE, 'w') as f:
                    json.dump(tokens, f)
                
                logger.info(f"Cleaned up {len(expired)} expired tokens")
                return len(expired)
        except Exception as e:
            logger.error(f"Error cleaning up tokens: {e}")
            return 0
    
    return 0