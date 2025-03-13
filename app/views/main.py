from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from app.proxmox.api import (
    get_user_vms, get_vm_status, start_vm, stop_vm, 
    create_snapshot, get_snapshots, get_cluster_info,
    get_node_status, get_storage_status, get_cluster_resources
)
from app.models.folder import FolderManager
import datetime
import time

bp = Blueprint('main', __name__)

# Initialize folder manager
folder_manager = FolderManager(data_dir='app/data')

# Store historical data for charts
cpu_history = [0] * 12
memory_history = [0] * 12
last_history_update = 0

@bp.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('main.dashboard'))

@bp.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    user = session['user']
    
    try:
        # Get all the cluster information we need
        update_history_data()
        
        # Get user VMs
        vms = get_user_vms(user['username'], user['groups'])
        running_vms = [vm for vm in vms if vm.get('status') == 'running']
        
        # Get cluster info
        cluster_info = get_cluster_info()
        
        # Get node status
        node_status = get_node_status()
        
        # Get storage status
        storage_status = get_storage_status()
        
        # Get resource usage
        resources = get_cluster_resources()
        
        # Calculate cluster totals
        cluster_cpu_total = sum(node.get('maxcpu', 0) for node in node_status if node.get('online'))
        cluster_cpu_used = sum(node.get('cpu', 0) * node.get('maxcpu', 0) for node in node_status if node.get('online'))
        cluster_cpu_percent = round((cluster_cpu_used / cluster_cpu_total * 100) if cluster_cpu_total > 0 else 0, 1)
        
        cluster_mem_total = round(sum(node.get('maxmem', 0) / (1024**3) for node in node_status if node.get('online')), 1)
        cluster_mem_used = round(sum(node.get('mem', 0) / (1024**3) for node in node_status if node.get('online')), 1)
        cluster_mem_percent = round((cluster_mem_used / cluster_mem_total * 100) if cluster_mem_total > 0 else 0, 1)
        
        cluster_storage_total = round(sum(storage.get('total', 0) / (1024**3) for storage in storage_status if storage.get('active')), 1)
        cluster_storage_used = round(sum(storage.get('used', 0) / (1024**3) for storage in storage_status if storage.get('active')), 1)
        cluster_storage_percent = round((cluster_storage_used / cluster_storage_total * 100) if cluster_storage_total > 0 else 0, 1)
        
        # Format node information for display
        for node in node_status:
            # Format uptime
            uptime_seconds = node.get('uptime', 0)
            if uptime_seconds > 0:
                days, remainder = divmod(uptime_seconds, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                if days > 0:
                    node['uptime_formatted'] = f"{int(days)}d {int(hours)}h {int(minutes)}m"
                elif hours > 0:
                    node['uptime_formatted'] = f"{int(hours)}h {int(minutes)}m"
                else:
                    node['uptime_formatted'] = f"{int(minutes)}m {int(seconds)}s"
            else:
                node['uptime_formatted'] = "N/A"
            
            # Calculate CPU and memory percentages
            node['cpu_percent'] = round(node.get('cpu', 0) * 100, 1)
            
            mem_total = node.get('maxmem', 0) / (1024**3)
            mem_used = node.get('mem', 0) / (1024**3)
            node['mem_total'] = round(mem_total, 1)
            node['mem_used'] = round(mem_used, 1)
            node['mem_percent'] = round((mem_used / mem_total * 100) if mem_total > 0 else 0, 1)
            
            # Count VMs on this node
            node['vm_count'] = len([vm for vm in vms if vm.get('node') == node.get('node')])
        
        # Format storage information
        for storage in storage_status:
            storage['total'] = round(storage.get('total', 0) / (1024**3), 1)
            storage['used'] = round(storage.get('used', 0) / (1024**3), 1)
            storage['avail'] = round(storage.get('avail', 0) / (1024**3), 1)
            storage['usage_percent'] = round((storage.get('used', 0) / storage.get('total', 0) * 100) if storage.get('total', 0) > 0 else 0, 1)
        
        # Get VM folder tree
        folder_structure = folder_manager.get_folder_structure()
        vm_folder_tree = folder_manager.build_folder_html(folder_structure, folder_structure[1], vms)
        
        return render_template(
            'dashboard.html', 
            user=user, 
            vms=vms, 
            cluster_info=cluster_info,
            node_status=node_status,
            storage_status=storage_status,
            vm_folder_tree=vm_folder_tree,
            
            # Cluster resource summaries
            cluster_cpu_total=cluster_cpu_total,
            cluster_cpu_used=round(cluster_cpu_used, 1),
            cluster_cpu_percent=cluster_cpu_percent,
            
            cluster_mem_total=cluster_mem_total,
            cluster_mem_used=cluster_mem_used,
            cluster_mem_percent=cluster_mem_percent,
            
            cluster_storage_total=cluster_storage_total,
            cluster_storage_used=cluster_storage_used,
            cluster_storage_percent=cluster_storage_percent,
            
            # Historical data for charts
            cpu_history=cpu_history,
            memory_history=memory_history
        )
    except Exception as e:
        import traceback
        # Handle errors gracefully
        flash(f"Error connecting to Proxmox API: {str(e)}", "error")
        print(traceback.format_exc())
        return render_template(
            'dashboard.html', 
            user=user, 
            vms=[], 
            api_error=True
        )

def update_history_data():
    global cpu_history, memory_history, last_history_update
    
    # Only update every 5 minutes
    current_time = time.time()
    if current_time - last_history_update < 300:  # 5 minutes = 300 seconds
        return
    
    try:
        # Get node status to update history
        node_status = get_node_status()
        
        if node_status:
            # Calculate current cluster CPU and memory usage
            cluster_cpu_total = sum(node.get('maxcpu', 0) for node in node_status if node.get('online'))
            cluster_cpu_used = sum(node.get('cpu', 0) * node.get('maxcpu', 0) for node in node_status if node.get('online'))
            cluster_cpu_percent = round((cluster_cpu_used / cluster_cpu_total * 100) if cluster_cpu_total > 0 else 0, 1)
            
            cluster_mem_total = sum(node.get('maxmem', 0) for node in node_status if node.get('online'))
            cluster_mem_used = sum(node.get('mem', 0) for node in node_status if node.get('online'))
            cluster_mem_percent = round((cluster_mem_used / cluster_mem_total * 100) if cluster_mem_total > 0 else 0, 1)
            
            # Shift historical data to make room for new point
            cpu_history.pop(0)
            cpu_history.append(cluster_cpu_percent)
            
            memory_history.pop(0)
            memory_history.append(cluster_mem_percent)
            
            last_history_update = current_time
    except Exception as e:
        print(f"Error updating historical data: {str(e)}")

# Add an API endpoint for updating dashboard data
@bp.route('/api/cluster-stats', methods=['GET'])
def get_cluster_stats():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        update_history_data()
        
        user = session['user']
        vms = get_user_vms(user['username'], user['groups'])
        node_status = get_node_status()
        
        return jsonify({
            'success': True,
            'vm_count': len(vms),
            'running_vm_count': len([vm for vm in vms if vm.get('status') == 'running']),
            'node_count': len(node_status),
            'online_node_count': len([node for node in node_status if node.get('online')]),
            'cpu_history': cpu_history,
            'memory_history': memory_history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/vm/<node>/<vmid>')
def vm_details(node, vmid):
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    vmtype = request.args.get('type', 'qemu')
    user = session['user']
    
    try:
        # Get VMs for sidebar
        vms = get_user_vms(user['username'], user['groups'])
        
        # Get VM folder tree
        folder_structure = folder_manager.get_folder_structure()
        vm_folder_tree = folder_manager.build_folder_html(folder_structure, folder_structure[1], vms)
        
        # Get VM status and details
        vm_status = get_vm_status(node, vmid, vmtype)
        snapshots = get_snapshots(node, vmid, vmtype)
        
        return render_template(
            'vm_details.html',
            user=user,
            vm_status=vm_status,
            snapshots=snapshots,
            node=node,
            vmid=vmid,
            vmtype=vmtype,
            vm_folder_tree=vm_folder_tree
        )
    except Exception as e:
        flash(f"Error retrieving VM details: {str(e)}", "error")
        return redirect(url_for('main.dashboard'))

@bp.route('/console/<node>/<vmid>')
def console(node, vmid):
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    vmtype = request.args.get('type', 'qemu')
    user = session['user']
    
    # For console pages, we hide the sidebar
    return render_template(
        'console.html',
        user=user,
        node=node,
        vmid=vmid,
        vmtype=vmtype,
        hide_sidebar=True  # Hide sidebar for console view
    )

# API routes for AJAX calls
@bp.route('/api/vm/<node>/<vmid>/start', methods=['POST'])
def api_start_vm(node, vmid):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    vmtype = request.args.get('type', 'qemu')
    
    result = start_vm(node, vmid, vmtype)
    if result is not None:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to start VM'}), 500

@bp.route('/api/vm/<node>/<vmid>/stop', methods=['POST'])
def api_stop_vm(node, vmid):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    vmtype = request.args.get('type', 'qemu')
    
    result = stop_vm(node, vmid, vmtype)
    if result is not None:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to stop VM'}), 500

@bp.route('/api/vm/<node>/<vmid>/snapshot', methods=['POST'])
def api_create_snapshot(node, vmid):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    vmtype = request.args.get('type', 'qemu')
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        return jsonify({'error': 'Snapshot name is required'}), 400
    
    result = create_snapshot(node, vmid, name, description, vmtype)
    if result is not None:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to create snapshot'}), 500
    
@bp.route('/test-connection')
def test_connection():
    """Test connection to Proxmox API"""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    from app.proxmox.api import get_api
    import traceback
    
    try:
        api = get_api()
        # Try to get a simple endpoint
        version = api.get_request("version")
        
        if version:
            return f"""
            <h1>Connection successful!</h1>
            <pre>{version}</pre>
            <p><a href="{url_for('main.dashboard')}">Return to dashboard</a></p>
            """
        else:
            return f"""
            <h1>Connection failed!</h1>
            <p>Unable to get version information from Proxmox API.</p>
            <p>Check that your credentials and server information are correct.</p>
            <p><a href="{url_for('main.dashboard')}">Return to dashboard</a></p>
            """
    except Exception as e:
        error_details = traceback.format_exc()
        return f"""
        <h1>Connection error!</h1>
        <p>Exception: {str(e)}</p>
        <pre>{error_details}</pre>
        <p><a href="{url_for('main.dashboard')}">Return to dashboard</a></p>
        """

@bp.route('/api/vm/<node>/<vmid>/vncproxy', methods=['POST'])
def vm_vncproxy(node, vmid):
    """Get a VNC proxy ticket for a VM"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    vmtype = request.args.get('type', 'qemu')
    
    try:
        api = get_api()
        
        if vmtype == 'qemu':
            endpoint = f"nodes/{node}/qemu/{vmid}/vncproxy"
        else:  # LXC container
            endpoint = f"nodes/{node}/lxc/{vmid}/vncproxy"
        
        # Enable console if needed
        vnc_info = api.post_request(endpoint, {})
        
        if vnc_info:
            return jsonify({
                'success': True,
                'data': vnc_info
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to get VNC proxy'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/vm/<node>/<vmid>/vnc', methods=['GET'])
def vm_vnc_websocket(node, vmid):
    """WebSocket proxy for VNC connection"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'No token provided'}), 400
    
    # This is a placeholder. In a production environment, you'd need to implement
    # a proper WebSocket proxy that connects to the Proxmox VNC server.
    # For a complete implementation, you'd need to use a library like websockify
    # or implement a custom WebSocket server.
    
    return jsonify({
        'success': False,
        'error': 'WebSocket proxy not implemented'
    }), 501

@bp.route('/api/vm/<node>/<vmid>/reboot', methods=['POST'])
def api_reboot_vm(node, vmid):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    vmtype = request.args.get('type', 'qemu')
    
    result = reboot_vm(node, vmid, vmtype)
    if result is not None:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to reboot VM'}), 500