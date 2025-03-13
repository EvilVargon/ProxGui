from flask import Blueprint, render_template, session, redirect, url_for, request, Response
import requests
from app.proxmox.api import get_api

bp = Blueprint('console', __name__, url_prefix='/console')

@bp.route('/<node>/<vmid>')
def vm_console(node, vmid):
    """Render the console page for a VM"""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    vmtype = request.args.get('type', 'qemu')
    user = session['user']
    
    # For simplicity, we'll render a template with noVNC that connects directly to Proxmox
    # In a production app, you might want to proxy this connection for security
    return render_template(
        'console.html',
        user=user,
        node=node,
        vmid=vmid,
        vmtype=vmtype
    )

@bp.route('/<node>/<vmid>/websockify')
def websockify(node, vmid):
    """
    Proxy the websocket connection to the Proxmox VNC console
    This is a very simple implementation that demonstrates the concept
    In production, you'd want a more robust solution using proper websocket libraries
    """
    if 'user' not in session:
        return Response("Unauthorized", 401)
    
    vmtype = request.args.get('type', 'qemu')
    api = get_api()
    
    # Get a VNC ticket from Proxmox
    if vmtype == 'qemu':
        endpoint = f"nodes/{node}/qemu/{vmid}/vncproxy"
    else:  # LXC container
        endpoint = f"nodes/{node}/lxc/{vmid}/vncproxy"
    
    vnc_info = api.post_request(endpoint, {})
    
    if not vnc_info:
        return Response("Failed to get VNC proxy", 500)
    
    # In a real implementation, you would now establish a websocket connection
    # between the client and the Proxmox VNC server using the ticket
    # This is beyond the scope of this example, as it requires a proper websocket proxy
    
    # For now, we'll just return the VNC info that would be used to establish the connection
    return Response(
        f"VNC connection info: {vnc_info}",
        200,
        {"Content-Type": "text/plain"}
    )