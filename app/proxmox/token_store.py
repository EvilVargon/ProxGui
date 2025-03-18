# In app/proxmox/token_store.py
import os
import json
import time
import threading

# Fix the token file path - use an absolute path
TOKEN_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../websocket_tokens.json'))
TOKEN_LOCK = threading.Lock()

def save_token(token, data):
    """Save a token to the shared file"""
    print(f"DEBUG: Saving token {token} to file {TOKEN_FILE}")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    
    with TOKEN_LOCK:
        # Load existing tokens
        tokens = {}
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    tokens = json.load(f)
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
        
        print(f"DEBUG: Saved token {token} to file {TOKEN_FILE}")
        print(f"DEBUG: File now contains {len(tokens)} tokens")
    
    return True

def get_token(token):
    """Get a token from the shared file"""
    print(f"DEBUG: Looking up token {token} in file {TOKEN_FILE}")
    
    if not os.path.exists(TOKEN_FILE):
        print(f"DEBUG: Token file {TOKEN_FILE} does not exist")
        return None
    
    with TOKEN_LOCK:
        try:
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
                if token in tokens:
                    print(f"DEBUG: Found token {token} in file")
                    return tokens[token]
                else:
                    print(f"DEBUG: Token {token} not found in file")
                    print(f"DEBUG: Available tokens: {list(tokens.keys())}")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"DEBUG: Error reading token file: {e}")
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
                
                return len(expired)
        except Exception:
            return 0
    
    return 0