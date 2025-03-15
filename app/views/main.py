from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from app.proxmox.api import (
    get_user_vms, get_vm_status, start_vm, stop_vm, 
    create_snapshot, get_snapshots, get_cluster_info,
    get_node_status, get_storage_status, get_cluster_resources
)
from app.models.folder import FolderManager
import datetime
import time
import os
import json
import math

bp = Blueprint('main', __name__)

# Initialize folder manager
folder_manager = FolderManager(data_dir='app/data')

# Store historical data for charts with multiple time resolutions
# Using a hierarchical time-based storage approach
HISTORY_FILE = 'app/data/performance_history.json'

# Define time buckets for different resolutions
HOUR_BUCKET = 5 * 60  # 5 minutes in seconds
DAY_BUCKET = 30 * 60   # 30 minutes in seconds
WEEK_BUCKET = 3 * 3600  # 3 hours in seconds
MONTH_BUCKET = 12 * 3600  # 12 hours in seconds

# Initialize history storage structure
history = {
    'hour': {
        'resolution': HOUR_BUCKET,
        'datapoints': 12,  # Past hour: 12 points at 5-minute intervals
        'cpu': [],
        'memory': [],
        'timestamps': []
    },
    'day': {
        'resolution': DAY_BUCKET,
        'datapoints': 48,  # Past day: 48 points at 30-minute intervals
        'cpu': [],
        'memory': [],
        'timestamps': []
    },
    'week': {
        'resolution': WEEK_BUCKET,
        'datapoints': 56,  # Past week: 56 points at 3-hour intervals
        'cpu': [],
        'memory': [],
        'timestamps': []
    },
    'month': {
        'resolution': MONTH_BUCKET,
        'datapoints': 60,  # Past month: 60 points at 12-hour intervals
        'cpu': [],
        'memory': [],
        'timestamps': []
    },
    'last_update': 0
}

def init_history_data():
    """Initialize history data structure from file or with defaults"""
    global history
    
    # Create default empty data structures if needed
    for period in ['hour', 'day', 'week', 'month']:
        if not history[period]['cpu']:
            history[period]['cpu'] = [0] * history[period]['datapoints']
        if not history[period]['memory']:
            history[period]['memory'] = [0] * history[period]['datapoints']
        if not history[period]['timestamps']:
            history[period]['timestamps'] = [''] * history[period]['datapoints']
    
    # Try to load from file
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                loaded_data = json.load(f)
                
                # Update history with loaded data
                for period in ['hour', 'day', 'week', 'month']:
                    if period in loaded_data:
                        # Only use loaded data if it has the right number of datapoints
                        if ('cpu' in loaded_data[period] and 
                            len(loaded_data[period]['cpu']) == history[period]['datapoints']):
                            history[period]['cpu'] = loaded_data[period]['cpu']
                            history[period]['memory'] = loaded_data[period]['memory']
                            history[period]['timestamps'] = loaded_data[period]['timestamps']
                
                if 'last_update' in loaded_data:
                    history['last_update'] = loaded_data['last_update']
    except Exception as e:
        print(f"Error loading history data: {str(e)}")

def save_history_data():
    """Save all historical data to file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        
        # Add metadata
        data_to_save = history.copy()
        data_to_save['updated_at'] = datetime.datetime.now().isoformat()
        
        # Save to file
        with open(HISTORY_FILE, 'w') as f:
            json.dump(data_to_save, f)
    except Exception as e:
        print(f"Error saving history data: {str(e)}")

def get_formatted_timestamp(dt, period):
    """Format timestamp appropriately based on the period"""
    if period == 'hour':
        return dt.strftime('%H:%M')
    elif period == 'day':
        return dt.strftime('%H:%M')
    elif period == 'week':
        return dt.strftime('%a %H:%M')  # Day of week + time
    else:  # month
        return dt.strftime('%m-%d %H:%M')  # Month-day + time

def update_history_data():
    """Update all historical data at appropriate intervals"""
    global history
    
    current_time = time.time()
    last_update = history['last_update']
    
    # Only update if at least 5 minutes have passed (short-term data interval)
    if current_time - last_update < HOUR_BUCKET:
        return
    
    try:
        # Get current performance data
        node_status = get_node_status()
        
        if node_status:
            # Calculate cluster CPU and memory usage
            cluster_cpu_total = sum(node.get('maxcpu', 0) for node in node_status if node.get('online'))
            cluster_cpu_used = sum(node.get('cpu', 0) * node.get('maxcpu', 0) for node in node_status if node.get('online'))
            cluster_cpu_percent = round((cluster_cpu_used / cluster_cpu_total * 100) if cluster_cpu_total > 0 else 0, 1)
            
            cluster_mem_total = sum(node.get('maxmem', 0) for node in node_status if node.get('online'))
            cluster_mem_used = sum(node.get('mem', 0) for node in node_status if node.get('online'))
            cluster_mem_percent = round((cluster_mem_used / cluster_mem_total * 100) if cluster_mem_total > 0 else 0, 1)
            
            # Current time as datetime for formatting
            now = datetime.datetime.now()
            
            # Update data for each time period
            for period in ['hour', 'day', 'week', 'month']:
                # Check if this period should be updated based on its resolution
                period_resolution = history[period]['resolution']
                if current_time - last_update >= period_resolution or last_update == 0:
                    # Shift historical data to make room for new point
                    history[period]['cpu'].pop(0)
                    history[period]['cpu'].append(cluster_cpu_percent)
                    
                    history[period]['memory'].pop(0)
                    history[period]['memory'].append(cluster_mem_percent)
                    
                    # Format timestamp appropriate to the period
                    history[period]['timestamps'].pop(0)
                    history[period]['timestamps'].append(get_formatted_timestamp(now, period))
            
            # Update last update time
            history['last_update'] = current_time
            
            # Save history to file
            save_history_data()
    except Exception as e:
        print(f"Error updating historical data: {str(e)}")

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
    
    # Get time period from query parameter (default to 'hour')
    time_period = request.args.get('time_period', 'hour')
    if time_period not in ['hour', 'day', 'week', 'month']:
        time_period = 'hour'
    
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
        
        # Get performance data for the selected time period
        cpu_history = history[time_period]['cpu']
        memory_history = history[time_period]['memory']
        timestamps = history[time_period]['timestamps']
        
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
            
            # Historical data for charts
            cpu_history=cpu_history,
            memory_history=memory_history,
            history_timestamps=timestamps,
            current_time_period=time_period
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

# Add an API endpoint for updating dashboard data
@bp.route('/api/cluster-stats', methods=['GET'])
def get_cluster_stats():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get chart type and time period from query parameters
    chart_type = request.args.get('chart_type')
    time_period = request.args.get('time_period', 'hour')
    
    if time_period not in ['hour', 'day', 'week', 'month']:
        time_period = 'hour'
    
    try:
        update_history_data()
        
        # If a specific chart type is requested, return only data for that chart
        if chart_type in ['cpu', 'memory']:
            return jsonify({
                'success': True,
                'cpu_history': history[time_period]['cpu'] if chart_type == 'cpu' else [],
                'memory_history': history[time_period]['memory'] if chart_type == 'memory' else [],
                'history_timestamps': history[time_period]['timestamps'],
                'time_period': time_period
            })
        
        # Otherwise return all stats for the dashboard
        user = session['user']
        vms = get_user_vms(user['username'], user['groups'])
        node_status = get_node_status()
        
        return jsonify({
            'success': True,
            'vm_count': len(vms),
            'running_vm_count': len([vm for vm in vms if vm.get('status') == 'running']),
            'node_count': len(node_status),
            'online_node_count': len([node for node in node_status if node.get('online')]),
            'cpu_history': history[time_period]['cpu'],
            'memory_history': history[time_period]['memory'],
            'history_timestamps': history[time_period]['timestamps'],
            'time_period': time_period
        })
    except Exception as e:
        import traceback
        print(f"Error in API: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Initialize history data when module is loaded
init_history_data()

# Rest of the file remains unchanged