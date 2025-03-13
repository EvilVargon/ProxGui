# Proxmox User Portal

A user-friendly web interface for Proxmox VE that provides a simplified experience for end-users.

## Features

- Active Directory authentication
- User dashboard showing only owned VMs
- VM performance monitoring
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

6. Visit http://localhost:5000 in your browser

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

## Next Steps

This is a basic implementation. The following features need to be implemented:

1. Real Active Directory integration with LDAP
2. VM ownership based on AD groups
3. Full VM management operations
4. Embedded noVNC console
5. Proper error handling and logging