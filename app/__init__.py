from flask import Flask
from app.config import Config
import datetime
import os
import urllib3

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Create data directory if it doesn't exist
    os.makedirs('app/data', exist_ok=True)
    
    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.views.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.views.console import bp as console_bp
    app.register_blueprint(console_bp)
    
    from app.views.folder_api import bp as folder_api_bp
    app.register_blueprint(folder_api_bp)
    
    # Initialize Proxmox API connection pool
    from app.proxmox.api import init_proxmox_api
    init_proxmox_api(app)
    
    # Add template context processors
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.now()}
    
    # Add custom Jinja filter for date formatting
    @app.template_filter('datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
        if value is None:
            return ""
        return value.strftime(format)
    
    @app.template_filter('datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
        if value is None:
            return ""
        # Handle Unix timestamp (in seconds or milliseconds)
        if isinstance(value, (int, float)):
            if value > 1000000000000:  # If value is in milliseconds
                value = value / 1000
            return datetime.datetime.fromtimestamp(value).strftime(format)
        # If it's already a datetime object
        if isinstance(value, datetime.datetime):
            return value.strftime(format)
        return value

    return app