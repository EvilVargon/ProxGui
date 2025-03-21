# Proxmox User Portal

A user-friendly web interface for Proxmox VE that provides a simplified experience for end-users.

## Features

- Active Directory authentication [TODO]
- User dashboard showing only owned VMs [TODO]
- VM performance monitoring [TODO]
- Start/stop VM controls
- Create/restore snapshots
- Embedded noVNC console
- Simplified VM creation

## Setup and Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/proxmox-user-portal.git
   cd proxmox-user-portal
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your Proxmox credentials:
   ```
   SECRET_KEY=your-secret-key
   PROXMOX_HOST=your-proxmox-host.example.com
   PROXMOX_USER=root@pam
   PROXMOX_PASSWORD=your-password
   PROXMOX_VERIFY_SSL=False
   ```

5. Run the application:
   ```bash
   python run.py
   ```

6. For VNC console support, run the websockify proxy:
   ```bash
   python websockify_proxy.py &
   ```
   
   Alternatively, use the start script which handles both services:
   ```bash
   ./start.sh
   ```

7. Visit http://localhost:5000 in your browser

## Project Structure

- `app/`: Main application directory
  - `__init__.py`: Flask application factory
  - `config.py`: Configuration settings
  - `auth/`: Authentication related code
  - `proxmox/`: Proxmox API interactions
  - `static/`: CSS, JavaScript, images
  - `templates/`: HTML templates
  - `views/`: View functions
- `requirements.txt`: Python dependencies
- `run.py`: Application entry point
- `websockify_proxy.py`: WebSocket proxy for VNC connections
- `start.sh`: Script to start both Flask app and WebSocket proxy

## Troubleshooting VNC Console

If you experience issues with the VNC console:

1. Ensure the websockify proxy is running:
   ```bash
   ps aux | grep websockify
   ```

2. Check if the required port (8765) is available:
   ```bash
   nc -z localhost 8765 || echo "Port available"
   ```

3. Run the VNC fix script:
   ```bash
   ./fix_vnc_complete.sh
   ```

4. Use the debugging tool to view token information:
   ```bash
   ./debug_websockify.py display
   ```

5. Check the logs for errors:
   ```bash
   cat websockify.log
   ```