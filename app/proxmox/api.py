import requests
import json
from flask import current_app
import time

import requests
import json
import time
import threading
from flask import current_app, g

# Global connection pool
_api_instances = {}
_api_lock = threading.RLock()

class ProxmoxAPI:
    def __init__(self, host, user, password, port=8006, verify_ssl=True):
        """
        Initialize the Proxmox API connector
        
        Args:
            host: The hostname or IP of any node in the Proxmox cluster (without http/https)
            user: Username with API access (e.g., 'user@pam')
            password: Password for the user
            port: Port number (default: 8006 for Proxmox)
            verify_ssl: Whether to verify SSL certificates
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.verify_ssl = verify_ssl
        self.token = None
        self.csrf_token = None
        self.token_timestamp = 0
        self.session = requests.Session()
        
        # Configure session
        if not verify_ssl:
            self.session.verify = False
        
        # Initial login
        self.login()
    
    def login(self):
        """Authenticate with Proxmox API and get access tokens"""
        url = f"https://{self.host}:{self.port}/api2/json/access/ticket"
        data = {
            "username": self.user,
            "password": self.password
        }
        
        try:
            print(f"Attempting to connect to {url}")
            response = self.session.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()['data']
                self.token = result['ticket']
                self.csrf_token = result['CSRFPreventionToken']
                self.token_timestamp = time.time()
                
                # Add cookie to session
                self.session.cookies.set("PVEAuthCookie", self.token, domain=self.host)
                
                print("Login successful!")
                return True
            else:
                print(f"Login failed with status code: {response.status_code}")
                if response.text:
                    print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"Exception during login: {str(e)}")
            return False
    
    def _check_token(self):
        """Check if token needs refresh (every 2 hours)"""
        if time.time() - self.token_timestamp > 7100:  # ~2 hours
            self.login()
    
    def get_request(self, endpoint, params=None):
        """Make a GET request to the Proxmox API
        
        Args:
            endpoint: API endpoint path
            params: Optional dictionary of query parameters
        """
        self._check_token()
        url = f"https://{self.host}:{self.port}/api2/json/{endpoint}"
        headers = {"Cookie": f"PVEAuthCookie={self.token}"}
        
        try:
            response = self.session.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()['data']
            else:
                print(f"GET request failed for {endpoint}: {response.status_code}")
                if response.text:
                    print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"Exception during GET request: {str(e)}")
            return None
    
    def post_request(self, endpoint, data):
        """Make a POST request to the Proxmox API"""
        self._check_token()
        url = f"https://{self.host}:{self.port}/api2/json/{endpoint}"
        headers = {
            "Cookie": f"PVEAuthCookie={self.token}",
            "CSRFPreventionToken": self.csrf_token
        }
        
        try:
            response = self.session.post(url, headers=headers, data=data, timeout=10)
            
            if response.status_code in [200, 201]:
                return response.json()['data']
            else:
                print(f"POST request failed for {endpoint}: {response.status_code}")
                if response.text:
                    print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"Exception during POST request: {str(e)}")
            return None
    
    def close(self):
        """Close the session"""
        self.session.close()

def get_api():
    """
    Get or create a Proxmox API connection from the connection pool.
    Uses Flask's application context for thread safety.
    """
    # First check if an instance already exists in the current request context
    if hasattr(g, 'proxmox_api'):
        return g.proxmox_api
    
    config = current_app.config
    
    # Create a unique key for this connection based on config
    conn_key = f"{config['PROXMOX_HOST']}:{config.get('PROXMOX_PORT', 8006)}-{config['PROXMOX_USER']}"
    
    # Thread-safe access to connection pool
    with _api_lock:
        if conn_key in _api_instances:
            api = _api_instances[conn_key]
            # Check if we need to refresh the token
            api._check_token()
        else:
            # Create new connection
            api = ProxmoxAPI(
                host=config['PROXMOX_HOST'],
                user=config['PROXMOX_USER'],
                password=config['PROXMOX_PASSWORD'],
                port=config.get('PROXMOX_PORT', 8006),
                verify_ssl=config['PROXMOX_VERIFY_SSL']
            )
            _api_instances[conn_key] = api
    
    # Store in Flask's g object for this request
    g.proxmox_api = api
    return api

# Add teardown function to Flask app
def init_proxmox_api(app):
    """Initialize the Proxmox API connection pool for a Flask app"""
    @app.teardown_appcontext
    def close_proxmox_api(exception=None):
        """Close Proxmox API connection at the end of a request"""
        api = getattr(g, 'proxmox_api', None)
        if api is not None:
            # Don't actually close it, just remove from g
            # The connection stays in the pool for reuse
            pass

def get_cluster_info():
    """Get information about the cluster and its nodes"""
    api = get_api()
    
    # Get the cluster status
    cluster_status = api.get_request("cluster/status")
    if cluster_status is None:
        return None
    
    # Get the resource pools for later use
    pools = api.get_request("pools")
    
    return {
        'status': cluster_status,
        'pools': pools
    }

def get_all_vms():
    """Get all VMs from all nodes in the cluster"""
    api = get_api()
    
    # First try to use the cluster resources endpoint, which gives us all resources in one call
    cluster_resources = api.get_request("cluster/resources")
    
    # If that fails, fall back to fetching node by node
    if cluster_resources is None:
        # Get cluster nodes
        nodes = api.get_request("nodes")
        
        # Handle the case where API connection fails
        if nodes is None:
            return []
            
        all_vms = []
        
        for node in nodes:
            # Get both VMs and containers
            vms = api.get_request(f"nodes/{node['node']}/qemu")
            if vms:
                for vm in vms:
                    vm['node'] = node['node']
                    vm['type'] = 'qemu'
                all_vms.extend(vms)
            
            containers = api.get_request(f"nodes/{node['node']}/lxc")
            if containers:
                for container in containers:
                    container['node'] = node['node']
                    container['type'] = 'lxc'
                all_vms.extend(containers)
        
        return all_vms
    
    # If cluster resources endpoint worked, filter for VMs and containers
    vms_and_containers = [
        resource for resource in cluster_resources
        if resource['type'] in ['qemu', 'lxc']
    ]
    
    return vms_and_containers

def get_user_vms(username, groups):
    """
    Get VMs that belong to a user based on their AD groups
    In a real implementation, this would filter VMs based on tags/notes/pool that match the user's groups
    """
    try:
        all_vms = get_all_vms()
        user_vms = []
        
        # In a real implementation, you'd filter based on your mapping between
        # AD groups and Proxmox pools, tags, or other identifiers
        
        # This is a very simplistic example that assumes:
        # 1. Each VM has a 'pool' attribute that corresponds to an AD group name
        # 2. Or you're using Proxmox's description field to store group info
        
        for vm in all_vms:
            # Check if VM is in a pool that matches one of the user's groups
            vm_pool = vm.get('pool', '')
            vm_description = vm.get('description', '')
            
            # Simple check - in reality, you'd have a more sophisticated mapping
            for group in groups:
                if (group.lower() in vm_pool.lower() or 
                    group.lower() in vm_description.lower()):
                    user_vms.append(vm)
                    break
            
            # For testing/demo purposes, return all VMs
            # Comment this out once you have real filtering logic
            if len(user_vms) == 0:
                user_vms = all_vms
        
        return user_vms
    except Exception as e:
        # Log the error in a production environment
        print(f"Error getting user VMs: {str(e)}")
        return []

def extract_vm_disks(config):
    """
    Extract disk information from VM/LXC configuration.
    Returns a list of disks with their type and size.
    
    Args:
        config: VM/LXC configuration dictionary from Proxmox API
    
    Returns:
        List of dictionaries with disk information (id, type, storage, size in GB)
    """
    disks = []
    
    # Common disk prefixes in Proxmox configurations
    disk_prefixes = ['scsi', 'virtio', 'ide', 'sata', 'mp', 'rootfs']
    
    for key, value in config.items():
        # Check if this is a disk entry
        disk_type = None
        for prefix in disk_prefixes:
            if key.startswith(prefix):
                disk_type = prefix
                break
        
        if not disk_type:
            continue
            
        # Initialize disk info
        disk_info = {
            'id': key,
            'type': disk_type
        }
        
        # Handle string configuration format
        if isinstance(value, str):
            # Parse comma-separated values
            parts = value.split(',')
            
            # Find storage information
            storage_part = value.split(':', 1)[0] if ':' in value else None
            if storage_part:
                disk_info['storage'] = storage_part
            
            # Find size information
            for part in parts:
                if part.startswith('size='):
                    size_str = part.split('=', 1)[1].strip()
                    
                    # Convert size to GB
                    try:
                        if size_str.endswith('G'):
                            disk_info['size'] = float(size_str[:-1])
                        elif size_str.endswith('T'):
                            disk_info['size'] = float(size_str[:-1]) * 1024
                        elif size_str.endswith('M'):
                            disk_info['size'] = float(size_str[:-1]) / 1024
                        else:
                            disk_info['size'] = float(size_str)
                    except (ValueError, TypeError):
                        # If we can't parse the size, skip it
                        pass
        
        # Handle dictionary configuration (common in LXC)
        elif isinstance(value, dict):
            if 'storage' in value:
                disk_info['storage'] = value['storage']
            if 'size' in value:
                try:
                    # Try to convert to float
                    size_value = value['size']
                    if isinstance(size_value, str):
                        if size_value.endswith('G'):
                            disk_info['size'] = float(size_value[:-1])
                        elif size_value.endswith('T'):
                            disk_info['size'] = float(size_value[:-1]) * 1024
                        elif size_value.endswith('M'):
                            disk_info['size'] = float(size_value[:-1]) / 1024
                        else:
                            disk_info['size'] = float(size_value)
                    else:
                        disk_info['size'] = float(size_value)
                except (ValueError, TypeError):
                    # If we can't parse the size, skip it
                    pass
        
        # Only add disks that have a size and make sure it's a number
        if 'size' in disk_info:
            try:
                # Ensure size is a number before rounding
                disk_info['size'] = round(float(disk_info['size']), 1)
                disks.append(disk_info)
            except (ValueError, TypeError):
                # If we can't convert to float for rounding, just skip this disk
                print(f"Warning: Could not process size for disk {key}: {disk_info.get('size', 'unknown')}")
                # If we still want to include this disk despite size issues, use:
                # del disk_info['size']  # Remove problematic size
                # disk_info['size'] = 0.0  # Or set a default
                # disks.append(disk_info)
        elif 'storage' in disk_info:
            # Include disks that have storage info but no size
            disk_info['size'] = 0.0  # Default size
            disks.append(disk_info)
    
    return disks

def get_vm_network_info(api, node, vmid, vmtype, networks):
    """
    Get network information for a VM, including IP addresses if available.
    
    Args:
        api: ProxmoxAPI instance
        node: Node name
        vmid: VM ID
        vmtype: VM type ('qemu' or 'lxc')
        networks: List of basic network interfaces from VM config
        
    Returns:
        Updated networks list with IP address information where available
    """
    # Only attempt to get agent info for running QEMU VMs
    if vmtype != 'qemu' or not networks:
        return networks
    
    try:
        # First check if the agent is running/enabled
        status_endpoint = f"nodes/{node}/qemu/{vmid}/status/current"
        status = api.get_request(status_endpoint)
        
        # Only proceed if agent is configured and VM is running
        if not status or status.get('status') != 'running' or status.get('agent') != 1:
            return networks
            
        # Check agent status before trying to use it
        agent_endpoint = f"nodes/{node}/qemu/{vmid}/agent/ping"
        ping_result = api.post_request(agent_endpoint, {})
        
        if not ping_result or 'result' not in ping_result:
            # Agent not responding
            return networks
            
        # Now try to get network interfaces
        agent_endpoint = f"nodes/{node}/qemu/{vmid}/agent/network-get-interfaces"
        agent_data = api.get_request(agent_endpoint)
        
        if not agent_data or 'result' not in agent_data:
            return networks
            
        network_interfaces = agent_data['result']
        
        # Add IP addresses to network interfaces
        for network in networks:
            for interface in network_interfaces:
                # Match by MAC address if available
                if 'hardware-address' in interface and 'hwaddr' in network:
                    if interface['hardware-address'].lower() == network['hwaddr'].lower():
                        ip_addresses = []
                        
                        if 'ip-addresses' in interface:
                            for ip_info in interface['ip-addresses']:
                                ip_addresses.append({
                                    'ip': ip_info.get('ip-address', ''),
                                    'prefix': ip_info.get('prefix', ''),
                                    'type': ip_info.get('ip-address-type', '')
                                })
                        
                        network['ip_addresses'] = ip_addresses
                        break
                
                # If no MAC match, try to match by name (for older agents)
                elif 'name' in interface and 'name' in network:
                    if interface['name'].lower() == network['name'].lower():
                        ip_addresses = []
                        
                        if 'ip-addresses' in interface:
                            for ip_info in interface['ip-addresses']:
                                ip_addresses.append({
                                    'ip': ip_info.get('ip-address', ''),
                                    'prefix': ip_info.get('prefix', ''),
                                    'type': ip_info.get('ip-address-type', '')
                                })
                        
                        network['ip_addresses'] = ip_addresses
                        break
        
    except Exception as e:
        print(f"Error getting network information for VM {vmid}: {str(e)}")
    
    return networks

def get_vm_status(node, vmid, vmtype='qemu'):
    """Get detailed status for a specific VM, including disks and network info"""
    api = get_api()
    
    if vmtype == 'qemu':
        endpoint = f"nodes/{node}/qemu/{vmid}/status/current"
    else:  # LXC container
        endpoint = f"nodes/{node}/lxc/{vmid}/status/current"
    
    status = api.get_request(endpoint)
    
    if not status:
        return None
        
    # Get config for additional info
    if vmtype == 'qemu':
        config_endpoint = f"nodes/{node}/qemu/{vmid}/config"
    else:  # LXC container
        config_endpoint = f"nodes/{node}/lxc/{vmid}/config"
        
    config = api.get_request(config_endpoint)
    
    if config:
        # Merge config into status
        status.update(config)
        
        # Extract disk information using the simplified function
        status['disks'] = extract_vm_disks(config)
        
        # Extract basic network interface information from config
        networks = []
        for key, value in config.items():
            if key.startswith('net') and isinstance(value, str):
                parts = value.split(',')
                net_info = {'id': key}
                
                for part in parts:
                    if '=' in part:
                        k, v = part.split('=', 1)
                        net_info[k] = v
                
                networks.append(net_info)
        
        # Get additional network info including IP addresses if available
        networks = get_vm_network_info(api, node, vmid, vmtype, networks)
        status['networks'] = networks
        
        # Try to get disk usage information for running VMs
        if vmtype == 'qemu' and status.get('status') == 'running':
            try:
                # Get disk usage from rrd data
                rrd_endpoint = f"nodes/{node}/qemu/{vmid}/rrddata"
                rrd_data = api.get_request(rrd_endpoint, params={
                    'timeframe': 'hour',
                    'cf': 'AVERAGE'
                })
                
                if rrd_data and len(rrd_data) > 0:
                    last_data = rrd_data[-1]
                    
                    # Get disk I/O rates
                    for disk in status['disks']:
                        disk_id = disk['id'].replace('-', '_')
                        read_key = f"disk_{disk_id}_read_bytes"
                        write_key = f"disk_{disk_id}_write_bytes"
                        
                        if read_key in last_data:
                            disk['read_rate'] = last_data[read_key]
                        if write_key in last_data:
                            disk['write_rate'] = last_data[write_key]
            except Exception as e:
                print(f"Error getting disk usage for VM {vmid}: {str(e)}")
        
    return status

def start_vm(node, vmid, vmtype='qemu'):
    """Start a VM or container"""
    api = get_api()
    
    if vmtype == 'qemu':
        endpoint = f"nodes/{node}/qemu/{vmid}/status/start"
    else:  # LXC container
        endpoint = f"nodes/{node}/lxc/{vmid}/status/start"
    
    return api.post_request(endpoint, {})

def stop_vm(node, vmid, vmtype='qemu'):
    """Stop a VM or container"""
    api = get_api()
    
    if vmtype == 'qemu':
        endpoint = f"nodes/{node}/qemu/{vmid}/status/stop"
    else:  # LXC container
        endpoint = f"nodes/{node}/lxc/{vmid}/status/stop"
    
    return api.post_request(endpoint, {})

def create_snapshot(node, vmid, name, description=None, vmtype='qemu'):
    """Create a snapshot of a VM"""
    api = get_api()
    
    if vmtype == 'qemu':
        endpoint = f"nodes/{node}/qemu/{vmid}/snapshot"
        data = {
            "snapname": name,
        }
        if description:
            data["description"] = description
        
        return api.post_request(endpoint, data)
    
    # For LXC, the endpoint is similar
    endpoint = f"nodes/{node}/lxc/{vmid}/snapshot"
    data = {
        "snapname": name,
    }
    if description:
        data["description"] = description
    
    return api.post_request(endpoint, data)

def get_snapshots(node, vmid, vmtype='qemu'):
    """Get list of snapshots for a VM"""
    api = get_api()
    
    if vmtype == 'qemu':
        endpoint = f"nodes/{node}/qemu/{vmid}/snapshot"
    else:  # LXC container
        endpoint = f"nodes/{node}/lxc/{vmid}/snapshot"
    
    return api.get_request(endpoint)

def get_node_status():
    """Get detailed status for all nodes in the cluster"""
    api = get_api()
    
    # Get cluster nodes
    nodes = api.get_request("nodes")
    
    if not nodes:
        return []
    
    node_status = []
    
    for node in nodes:
        # Skip node if it doesn't have a name
        if 'node' not in node:
            continue
            
        # Try to get detailed status if node is online
        detailed_status = None
        if node.get('status') == 'online':
            detailed_status = api.get_request(f"nodes/{node['node']}/status")
        
        # Combine basic and detailed status
        status = {**node}
        
        if detailed_status:
            status.update(detailed_status)
            status['online'] = True
        else:
            status['online'] = False
        
        node_status.append(status)
    
    return node_status

def get_storage_status():
    """Get status of all storage in the cluster"""
    api = get_api()
    
    # Get storage list
    storages = api.get_request("storage")
    
    if not storages:
        return []
    
    storage_status = []
    
    for storage in storages:
        # Skip if no content types defined
        if 'content' not in storage:
            continue
            
        # Get detailed storage info
        try:
            storage_details = api.get_request(f"nodes/{storage.get('node', 'localhost')}/storage/{storage['storage']}/status")
            
            # Create combined storage info
            storage_info = {**storage}
            
            if storage_details:
                storage_info.update(storage_details)
            
            # Set active status
            storage_info['active'] = storage.get('active', 0) == 1 and storage.get('enabled', 0) == 1
            
            # Calculate usage percentage
            if 'total' in storage_info and storage_info['total'] > 0:
                storage_info['usage_percent'] = round((storage_info.get('used', 0) / storage_info['total']) * 100, 1)
            else:
                storage_info['usage_percent'] = 0
                
            storage_status.append(storage_info)
        except Exception as e:
            print(f"Error getting details for storage {storage['storage']}: {str(e)}")
            # Add basic info even if detailed status fails
            storage['active'] = storage.get('active', 0) == 1 and storage.get('enabled', 0) == 1
            storage['usage_percent'] = 0
            storage_status.append(storage)
    
    return storage_status

def get_cluster_resources():
    """Get all resources in the cluster (VMs, storage, nodes)"""
    api = get_api()
    
    # Get cluster resources
    resources = api.get_request("cluster/resources")
    
    if not resources:
        return []
    
    return resources

def reboot_vm(node, vmid, vmtype='qemu'):
    """Reboot a VM or container"""
    api = get_api()
    
    if vmtype == 'qemu':
        endpoint = f"nodes/{node}/qemu/{vmid}/status/reboot"
    else:  # LXC container
        endpoint = f"nodes/{node}/lxc/{vmid}/status/reboot"
    
    return api.post_request(endpoint, {})