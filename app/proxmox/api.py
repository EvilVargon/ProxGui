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
        
        # Extract disk information
        disks = []
        disk_types = ['scsi', 'virtio', 'ide', 'sata', 'rootfs', 'unused']
        
        # Dictionaries to handle different storage mappings
        storage_mapping = {}
        
        # First, collect storage information
        for key, value in config.items():
            # Parse storage volumes
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
        
        # Then, collect disk sizes and configurations
        for key, value in config.items():
            # Look for specific disk type keys
            is_disk_key = any(key.startswith(disk_type) for disk_type in disk_types)
            
            try:
                # Handle both string and dictionary configurations
                if is_disk_key:
                    disk_info = {'id': key}
                    
                    # Handle different configuration types
                    if isinstance(value, str):
                        parts = value.split(',')
                        
                        for part in parts:
                            if '=' in part:
                                subkey, subval = part.split('=', 1)
                                
                                # Size parsing
                                if subkey == 'size':
                                    # Convert size to GB for different formats
                                    try:
                                        if isinstance(subval, str):
                                            # Strip any whitespace
                                            subval = subval.strip()
                                            
                                            # Handle various size formats
                                            if not subval:
                                                continue  # Skip empty values
                                            
                                            if subval.endswith('G'):
                                                disk_info['size'] = float(subval[:-1])
                                            elif subval.endswith('T'):
                                                disk_info['size'] = float(subval[:-1]) * 1024
                                            elif subval.endswith('M'):
                                                disk_info['size'] = float(subval[:-1]) / 1024
                                            else:
                                                # Try to convert direct numeric values
                                                disk_info['size'] = float(subval)
                                    except (ValueError, TypeError) as e:
                                        print(f"Could not parse size for {key}: {subval}. Error: {e}")
                                        continue  # Skip this disk if size can't be parsed
                                
                                # Volume reference
                                elif subkey.startswith('volume'):
                                    if subval in storage_mapping:
                                        disk_info['storage'] = storage_mapping[subval]['storage']
                                        disk_info['disk_path'] = storage_mapping[subval]['path']
                                
                                # Other metadata
                                elif subkey in ['format', 'media', 'cache']:
                                    disk_info[subkey] = subval
                        
                        # Fallback storage parsing
                        if 'storage' not in disk_info:
                            storage_parts = value.split(':')
                            if len(storage_parts) >= 2:
                                disk_info['storage'] = storage_parts[0]
                    
                    elif isinstance(value, dict):
                        # Direct dictionary configuration (for LXC containers)
                        if 'storage' in value:
                            disk_info['storage'] = value['storage']
                        if 'size' in value:
                            try:
                                # Ensure size is converted to float
                                disk_info['size'] = float(value['size'])
                            except (ValueError, TypeError) as e:
                                print(f"Could not parse size for {key}: {value['size']}. Error: {e}")
                                continue  # Skip this disk if size can't be parsed
                    
                    # Validate and add disk info
                    if 'size' in disk_info:
                        # Ensure size is always a float and rounded to 1 decimal
                        try:
                            disk_info['size'] = round(float(disk_info['size']), 1)
                        except (ValueError, TypeError) as e:
                            print(f"Rounding error for disk {key}: {e}")
                            disk_info['size'] = 0.0
                        
                        # Only add if we have meaningful information
                        if disk_info.get('storage') or disk_info.get('size') > 0:
                            disks.append(disk_info)
            except Exception as e:
                print(f"Error parsing disk {key}: {e}")
        
        # Fallback parsing if no disks found
        if not disks:
            try:
                # Check for LXC rootfs or other potential storage configurations
                for key, value in config.items():
                    if key == 'rootfs' or key.startswith('mp') or key.startswith('unused'):
                        try:
                            disk_info = {'id': key}
                            
                            # Handle different configuration types for LXC and unused disks
                            if isinstance(value, str):
                                # Typical LXC volume format: local:100/container.root
                                storage_parts = value.split(':')
                                if len(storage_parts) >= 2:
                                    disk_info['storage'] = storage_parts[0]
                                    
                                    # Try to extract size if possible
                                    size_match = storage_parts[1].split('/')
                                    if len(size_match) > 0:
                                        try:
                                            # Convert from MB to GB, handling potential non-numeric values
                                            size_str = size_match[0].strip()
                                            disk_info['size'] = round(float(size_str) / 1024, 1) if size_str else 0.0
                                        except (ValueError, TypeError):
                                            pass
                            
                            elif isinstance(value, dict):
                                # Direct dictionary configuration
                                if 'storage' in value:
                                    disk_info['storage'] = value['storage']
                                if 'size' in value:
                                    try:
                                        disk_info['size'] = round(float(value['size']), 1)
                                    except (ValueError, TypeError):
                                        pass
                            
                            # Add only if we have some meaningful information
                            if 'storage' in disk_info or (disk_info.get('size', 0) > 0):
                                disks.append(disk_info)
                        except Exception as e:
                            print(f"Fallback disk parsing error for {key}: {e}")
            except Exception as e:
                print(f"Final fallback disk parsing error: {e}")
        
        # Ensure disks are always a list, even if empty
        status['disks'] = disks if disks else [] 
        
        # Extract network information
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
        
        status['networks'] = networks
        
        # Try to get disk usage information
        if vmtype == 'qemu':
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
                    for disk in disks:
                        disk_id = disk['id'].replace('-', '_')
                        read_key = f"disk_{disk_id}_read_bytes"
                        write_key = f"disk_{disk_id}_write_bytes"
                        
                        if read_key in last_data:
                            disk['read_rate'] = last_data[read_key]
                        if write_key in last_data:
                            disk['write_rate'] = last_data[write_key]
            except Exception as e:
                print(f"Error getting disk usage for VM {vmid}: {str(e)}")
    
        # Try to get IP addresses
        if vmtype == 'qemu' and status.get('status') == 'running':
            try:
                agent_endpoint = f"nodes/{node}/qemu/{vmid}/agent/network-get-interfaces"
                agent_data = api.get_request(agent_endpoint)
                
                if agent_data and 'result' in agent_data:
                    network_interfaces = agent_data['result']
                    
                    # Add IP addresses to network interfaces
                    for network in networks:
                        for interface in network_interfaces:
                            if 'name' in interface and 'hardware-address' in interface and 'hwaddr' in network:
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