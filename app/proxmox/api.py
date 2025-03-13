import requests
import json
from flask import current_app
import time

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
            response = requests.post(url, data=data, verify=self.verify_ssl, timeout=10)
            
            if response.status_code == 200:
                result = response.json()['data']
                self.token = result['ticket']
                self.csrf_token = result['CSRFPreventionToken']
                self.token_timestamp = time.time()
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
    
    def get_request(self, endpoint):
        """Make a GET request to the Proxmox API"""
        self._check_token()
        url = f"https://{self.host}:{self.port}/api2/json/{endpoint}"
        headers = {"Cookie": f"PVEAuthCookie={self.token}"}
        
        try:
            response = requests.get(url, headers=headers, verify=self.verify_ssl, timeout=10)
            
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
            response = requests.post(url, headers=headers, data=data, verify=self.verify_ssl, timeout=10)
            
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

# Initialize the API connection
def get_api():
    """Get or create Proxmox API connection"""
    config = current_app.config
    return ProxmoxAPI(
        host=config['PROXMOX_HOST'],
        user=config['PROXMOX_USER'],
        password=config['PROXMOX_PASSWORD'],
        port=config.get('PROXMOX_PORT', 8006),
        verify_ssl=config['PROXMOX_VERIFY_SSL']
    )

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

def extract_disk_info(config, vmtype='qemu'):
    """
    Extract disk information from VM/container configuration.
    
    Args:
        config (dict): VM configuration dictionary from Proxmox API
        vmtype (str): Type of VM ('qemu' or 'lxc')
        
    Returns:
        list: List of dictionaries containing parsed disk information
    """
    disks = []
    
    # Return empty list if config is None or not a dictionary
    if not config or not isinstance(config, dict):
        return disks
    
    try:
        # Dictionary to store storage mappings
        storage_mapping = {}
        
        # First collect storage information/mappings
        for key, value in config.items():
            if key.startswith('volume') and isinstance(value, str):
                try:
                    storage_parts = value.split(':')
                    if len(storage_parts) >= 2:
                        storage_mapping[key] = {
                            'storage': storage_parts[0],
                            'path': value
                        }
                except Exception as e:
                    print(f"Error parsing volume {key}: {e}")
        
        # Different disk identifiers based on VM type
        if vmtype == 'qemu':
            # Disk type identifiers for QEMU VMs
            disk_types = ['scsi', 'virtio', 'ide', 'sata', 'efidisk', 'tpmstate']
        else:
            # Disk type identifiers for LXC containers
            disk_types = ['rootfs', 'mp', 'unused']
        
        # Process all disk entries
        for key, value in config.items():
            # Check if this is a disk key
            is_disk_key = False
            
            # For standard disk types like scsi0, virtio0, etc.
            for disk_type in disk_types:
                if key == disk_type or key.startswith(f"{disk_type}"):
                    is_disk_key = True
                    break
            
            # Skip if not a disk key
            if not is_disk_key:
                continue
                
            # Start building disk info with ID from key
            disk_info = {'id': key}
            
            try:
                # Handle string configuration format (common for both QEMU VMs and LXC containers)
                if isinstance(value, str):
                    # Special handling for mount points in LXC containers
                    if key.startswith('mp'):
                        try:
                            # Typical format: local-lvm:vm-109-disk-1,mp=/dev/sdc,backup=1,size=100G
                            parts = value.split(',')
                            
                            # First part contains storage info
                            if ':' in parts[0]:
                                storage_parts = parts[0].split(':')
                                disk_info['storage'] = storage_parts[0]
                                disk_info['path'] = parts[0]
                            
                            # Extract mount point
                            for part in parts:
                                if part.startswith('mp='):
                                    disk_info['mount_point'] = part.split('=', 1)[1]
                                    break
                            
                            # Process other parameters
                            for part in parts:
                                if '=' in part:
                                    param_key, param_value = part.split('=', 1)
                                    param_key = param_key.strip()
                                    param_value = param_value.strip()
                                    
                                    # Size parsing
                                    if param_key == 'size':
                                        try:
                                            # Handle size with suffix
                                            if param_value.endswith('G'):
                                                disk_info['size'] = float(param_value[:-1])
                                            elif param_value.endswith('T'):
                                                disk_info['size'] = float(param_value[:-1]) * 1024
                                            elif param_value.endswith('M'):
                                                disk_info['size'] = float(param_value[:-1]) / 1024
                                            elif param_value.endswith('K'):
                                                disk_info['size'] = float(param_value[:-1]) / (1024 * 1024)
                                            else:
                                                disk_info['size'] = float(param_value)
                                        except (ValueError, TypeError) as e:
                                            print(f"Could not parse size for {key}: {param_value}. Error: {e}")
                                    
                                    # Other parameters
                                    elif param_key not in ['mp']:  # Skip already processed params
                                        disk_info[param_key] = param_value
                        except Exception as e:
                            print(f"Error parsing mount point {key}: {e}")
                    
                    # Special handling for rootfs in LXC containers
                    elif key == 'rootfs':
                        try:
                            # Typical format: local-lvm:vm-109-disk-0,size=64G
                            parts = value.split(',')
                            
                            # First part contains storage info
                            if ':' in parts[0]:
                                storage_parts = parts[0].split(':')
                                disk_info['storage'] = storage_parts[0]
                                disk_info['path'] = parts[0]
                            
                            # Process parameters
                            for part in parts:
                                if '=' in part:
                                    param_key, param_value = part.split('=', 1)
                                    param_key = param_key.strip()
                                    param_value = param_value.strip()
                                    
                                    # Size parsing
                                    if param_key == 'size':
                                        try:
                                            # Handle size with suffix
                                            if param_value.endswith('G'):
                                                disk_info['size'] = float(param_value[:-1])
                                            elif param_value.endswith('T'):
                                                disk_info['size'] = float(param_value[:-1]) * 1024
                                            elif param_value.endswith('M'):
                                                disk_info['size'] = float(param_value[:-1]) / 1024
                                            elif param_value.endswith('K'):
                                                disk_info['size'] = float(param_value[:-1]) / (1024 * 1024)
                                            else:
                                                disk_info['size'] = float(param_value)
                                        except (ValueError, TypeError) as e:
                                            print(f"Could not parse size for {key}: {param_value}. Error: {e}")
                                    
                                    # Other parameters
                                    else:
                                        disk_info[param_key] = param_value
                        except Exception as e:
                            print(f"Error parsing rootfs {key}: {e}")
                    
                    # Standard disk parsing for QEMU VMs and other formats
                    else:
                        # Split by commas to get parameters
                        parts = value.split(',')
                        
                        # First part may contain storage info
                        if ':' in parts[0]:
                            storage_parts = parts[0].split(':')
                            if len(storage_parts) >= 2:
                                disk_info['storage'] = storage_parts[0]
                                disk_info['path'] = parts[0]
                        
                        # Process parameters
                        for part in parts:
                            if '=' in part:
                                param_key, param_value = part.split('=', 1)
                                param_key = param_key.strip()
                                param_value = param_value.strip()
                                
                                # Size parsing
                                if param_key == 'size':
                                    try:
                                        # Handle size with suffix
                                        if param_value.endswith('G'):
                                            disk_info['size'] = float(param_value[:-1])
                                        elif param_value.endswith('T'):
                                            disk_info['size'] = float(param_value[:-1]) * 1024
                                        elif param_value.endswith('M'):
                                            disk_info['size'] = float(param_value[:-1]) / 1024
                                        elif param_value.endswith('K'):
                                            disk_info['size'] = float(param_value[:-1]) / (1024 * 1024)
                                        else:
                                            disk_info['size'] = float(param_value)
                                    except (ValueError, TypeError) as e:
                                        print(f"Could not parse size for {key}: {param_value}. Error: {e}")
                                
                                # Volume reference
                                elif param_key == 'volume':
                                    if param_value in storage_mapping:
                                        disk_info['storage'] = storage_mapping[param_value]['storage']
                                        disk_info['path'] = storage_mapping[param_value]['path']
                                
                                # Important metadata
                                elif param_key in ['format', 'media', 'cache', 'iothread', 'discard', 'backup']:
                                    disk_info[param_key] = param_value
                
                # Handle dictionary configuration format (less common)
                elif isinstance(value, dict):
                    # Direct dictionary configuration
                    if 'storage' in value:
                        disk_info['storage'] = value['storage']
                    
                    if 'size' in value:
                        try:
                            size_value = value['size']
                            
                            # Handle size with suffix if it's a string
                            if isinstance(size_value, str):
                                size_value = size_value.strip()
                                if size_value.endswith('G'):
                                    disk_info['size'] = float(size_value[:-1])
                                elif size_value.endswith('T'):
                                    disk_info['size'] = float(size_value[:-1]) * 1024
                                elif size_value.endswith('M'):
                                    disk_info['size'] = float(size_value[:-1]) / 1024
                                elif size_value.endswith('K'):
                                    disk_info['size'] = float(size_value[:-1]) / (1024 * 1024)
                                else:
                                    disk_info['size'] = float(size_value)
                            else:
                                # If it's already a number
                                disk_info['size'] = float(size_value)
                        except (ValueError, TypeError) as e:
                            print(f"Could not parse size for {key}: {value['size']}. Error: {e}")
                    
                    # Copy other important metadata
                    for meta_key in ['format', 'media', 'cache', 'iothread', 'path', 'mount_point', 'backup']:
                        if meta_key in value:
                            disk_info[meta_key] = value[meta_key]
                
                # Add disk type info based on key prefix
                for disk_type in disk_types:
                    if key == disk_type or key.startswith(f"{disk_type}"):
                        disk_info['type'] = disk_type
                        break
                
                # Special disk type labels for better UI display
                if key == 'rootfs':
                    disk_info['type_label'] = 'Root Filesystem'
                elif key.startswith('mp'):
                    disk_info['type_label'] = 'Mount Point'
                elif key.startswith('scsi'):
                    disk_info['type_label'] = 'SCSI Disk'
                elif key.startswith('virtio'):
                    disk_info['type_label'] = 'VirtIO Disk'
                elif key.startswith('ide'):
                    disk_info['type_label'] = 'IDE Disk'
                elif key.startswith('sata'):
                    disk_info['type_label'] = 'SATA Disk'
                elif key.startswith('efidisk'):
                    disk_info['type_label'] = 'EFI Disk'
                
                # Validate size and add disk info to the list
                if 'size' in disk_info:
                    try:
                        # Ensure size is a float and rounded to 1 decimal
                        disk_info['size'] = round(float(disk_info['size']), 1)
                    except (ValueError, TypeError) as e:
                        print(f"Error rounding size for disk {key}: {e}")
                        disk_info['size'] = 0.0
                
                # Add the disk to our list if it has either storage, size, or mount point info
                if ('storage' in disk_info or 
                    ('size' in disk_info and disk_info['size'] > 0) or
                    'mount_point' in disk_info):
                    disks.append(disk_info)
                
            except Exception as e:
                print(f"Error processing disk {key}: {e}")
        
        # Sort disks by a sensible order - rootfs first, then mount points, then other disks
        def disk_sort_key(disk):
            # Primary sort by disk type
            if disk['id'] == 'rootfs':
                type_order = 0  # Rootfs first
            elif disk['id'].startswith('mp'):
                type_order = 1  # Mount points second
            else:
                type_order = 2  # Other disks last
            
            # Secondary sort by disk ID to maintain consistent order
            # Extract numeric part from IDs like mp0, scsi0, etc.
            id_num = 0
            try:
                # Try to extract a number from the end of the ID
                id_str = ''.join(filter(str.isdigit, disk['id']))
                if id_str:
                    id_num = int(id_str)
            except (ValueError, TypeError):
                pass
            
            return (type_order, id_num)
        
        # Sort the disks
        disks.sort(key=disk_sort_key)
        
    except Exception as e:
        print(f"Error extracting disk information: {e}")
    
    return disks


def extract_network_info(config):
    """
    Extract network interface information from VM/container configuration.
    
    Args:
        config (dict): VM configuration dictionary from Proxmox API
        
    Returns:
        list: List of dictionaries containing parsed network interface information
    """
    networks = []
    
    # Return empty list if config is None or not a dictionary
    if not config or not isinstance(config, dict):
        return networks
    
    try:
        # Look for network interfaces (net0, net1, etc.)
        for key, value in config.items():
            if not key.startswith('net') or not isinstance(value, str):
                continue
            
            # Create base network info
            net_info = {'id': key}
            
            # Split parameters
            parts = value.split(',')
            
            # First part often contains model and MAC address
            if '=' in parts[0]:
                model, mac = parts[0].split('=', 1)
                net_info['model'] = model
                net_info['hwaddr'] = mac
            
            # Process remaining parameters
            for part in parts:
                if '=' in part:
                    param_key, param_value = part.split('=', 1)
                    param_key = param_key.strip()
                    param_value = param_value.strip()
                    
                    # Common network parameters
                    if param_key in ['bridge', 'tag', 'firewall', 'rate', 'mtu']:
                        net_info[param_key] = param_value
            
            networks.append(net_info)
        
        # Sort networks by ID for consistency
        networks.sort(key=lambda x: x['id'])
        
    except Exception as e:
        print(f"Error extracting network information: {e}")
    
    return networks

def get_vm_status(node, vmid, vmtype='qemu'):
    """Get detailed status for a specific VM, including disks and network info"""
    api = get_api()
    
    # Get current status
    if vmtype == 'qemu':
        endpoint = f"nodes/{node}/qemu/{vmid}/status/current"
    else:  # LXC container
        endpoint = f"nodes/{node}/lxc/{vmid}/status/current"
    
    status = api.get_request(endpoint)
    
    if not status:
        return None
        
    # Get VM configuration for additional info
    if vmtype == 'qemu':
        config_endpoint = f"nodes/{node}/qemu/{vmid}/config"
    else:  # LXC container
        config_endpoint = f"nodes/{node}/lxc/{vmid}/config"
        
    config = api.get_request(config_endpoint)
    
    if config:
        # Merge config into status
        status.update(config)
        
        # Extract disk information using our dedicated function
        status['disks'] = extract_disk_info(config, vmtype)
        
        # Extract network information using our dedicated function
        status['networks'] = extract_network_info(config)
        
        # Try to get disk usage information for running VMs
        if vmtype == 'qemu' and status.get('status') == 'running':
            try:
                # Get disk usage from rrd data
                rrd_endpoint = f"nodes/{node}/qemu/{vmid}/rrddata"
                rrd_data = api.get_request(rrd_endpoint)
                
                if rrd_data and len(rrd_data) > 0:
                    last_data = rrd_data[-1]
                    
                    # Add I/O rates to each disk
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
        
        # Try to get IP addresses for running VMs using qemu-agent
        if vmtype == 'qemu' and status.get('status') == 'running':
            try:
                agent_endpoint = f"nodes/{node}/qemu/{vmid}/agent/network-get-interfaces"
                agent_data = api.get_request(agent_endpoint)
                
                if agent_data and 'result' in agent_data:
                    network_interfaces = agent_data['result']
                    
                    # Add IP addresses to network interfaces
                    for network in status['networks']:
                        for interface in network_interfaces:
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
            except Exception as e:
                print(f"Error getting IP addresses for VM {vmid}: {str(e)}")
    
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