import os
import json
import time
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token store file path
TOKEN_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../websocket_tokens.json'))
TOKEN_LOCK = threading.Lock()

def save_token(token, data):
    """Save a token and its associated data"""
    logger.info(f"Saving token {token} to file")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    
    with TOKEN_LOCK:
        # Load existing tokens
        tokens = {}
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    tokens = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                # If file is corrupted, start fresh
                tokens = {}
        
        # Add token with timestamp
        tokens[token] = {
            'data': data,
            'created_at': time.time()
        }
        
        # Save to file
        with open(TOKEN_FILE, 'w') as f:
            json.dump(tokens, f)
        
        logger.info(f"Saved token {token} to file")
    
    return True

def get_token(token):
    """Get a token's data"""
    if not os.path.exists(TOKEN_FILE):
        logger.warning(f"Token file {TOKEN_FILE} does not exist")
        return None
    
    with TOKEN_LOCK:
        try:
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
                
                if token in tokens:
                    logger.info(f"Found token {token}")
                    return tokens[token]
                
                logger.warning(f"Token {token} not found")
                return None
        except Exception as e:
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
                # Remove tokens older than 5 minutes
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

# Start cleanup thread
def start_cleanup_thread():
    """Start a thread to periodically clean up expired tokens"""
    def cleanup_loop():
        while True:
            try:
                cleanup_tokens()
                time.sleep(60)  # Run every minute
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
    
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
