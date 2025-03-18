"""
Token storage for VNC connections - shared between Flask app and WebSocket server
"""
import json
import os
import time
import threading
import logging

logger = logging.getLogger(__name__)

# File to store tokens
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '../../websocket_tokens.json')

# Mutex for thread-safe operations
token_mutex = threading.Lock()

def load_tokens():
    """Load tokens from file"""
    try:
        if os.path.exists(TOKEN_FILE):
            with token_mutex:
                with open(TOKEN_FILE, 'r') as f:
                    tokens = json.load(f)
                    return tokens
        return {}
    except Exception as e:
        logger.exception(f"Error loading tokens: {e}")
        return {}

def save_tokens(tokens):
    """Save tokens to file"""
    try:
        with token_mutex:
            with open(TOKEN_FILE, 'w') as f:
                json.dump(tokens, f)
    except Exception as e:
        logger.exception(f"Error saving tokens: {e}")

def store_token(token, vnc_info, host, port, verify_ssl=True):
    """Store a token"""
    tokens = load_tokens()
    
    # Store token data
    tokens[token] = {
        'host': host,
        'port': port,
        'ticket': vnc_info.get('ticket'),
        'vnc_info': vnc_info,
        'created_at': time.time(),
        'verify_ssl': verify_ssl
    }
    
    save_tokens(tokens)
    logger.info(f"Stored token {token} to file")
    return token

def get_token(token):
    """Get token data"""
    tokens = load_tokens()
    return tokens.get(token)

def remove_token(token):
    """Remove a token"""
    tokens = load_tokens()
    if token in tokens:
        del tokens[token]
        save_tokens(tokens)
        return True
    return False

def clean_old_tokens():
    """Clean up expired tokens"""
    tokens = load_tokens()
    current_time = time.time()
    expired = []
    
    for token, data in tokens.items():
        if current_time - data.get('created_at', 0) > 300:  # 5 minutes
            expired.append(token)
    
    if expired:
        for token in expired:
            del tokens[token]
        save_tokens(tokens)
        logger.info(f"Cleaned {len(expired)} expired tokens")
    
    return len(expired)