from flask import Blueprint, jsonify, request, session
from app.proxmox.api import get_api, get_node_status, create_vm
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('vm_api', __name__, url_prefix='/api/vm')

@bp.route('/available-isos', methods=['GET'])
def available_isos():
    """Get available ISO images for VM creation"""
    if 'user' not in session:
        logger.warning("Unauthorized access attempt to available-isos")
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        logger.info("Fetching available ISO images")
        api = get_api()
        
        # Get available storage with ISO support
        storages = api.get_request("storage")
        iso_storages = []
        
        if storages:
            for storage in storages:
                # Check if storage supports ISO content
                if 'content' in storage and 'iso' in storage['content'].split(','):
                    iso_storages.append(storage)
                    logger.info(f"Found ISO storage: {storage['storage']}")
        else:
            logger.warning("Failed to retrieve storage list")
        
        # Fetch ISOs from each storage
        available_isos = []
        for storage in iso_storages:
            endpoint = f"nodes/{storage.get('node', 'localhost')}/storage/{storage['storage']}/content"
            params = {'content': 'iso'}
            
            logger.info(f"Querying endpoint for ISOs: {endpoint}")
            content = api.get_request(endpoint, params)
            
            if content:
                for iso in content:
                    available_isos.append({
                        'storage': storage['storage'],
                        'volid': iso.get('volid', ''),
                        'name': iso.get('volid', '').split('/')[-1],
                        'size': iso.get('size', 0),
                        'format': iso.get('format', '')
                    })
                    logger.info(f"Found ISO: {iso.get('volid', '').split('/')[-1]}")
        
        logger.info(f"Returning {len(available_isos)} ISOs")
        return jsonify({
            'success': True,
            'isos': available_isos
        })
    except Exception as e:
        error_tb = traceback.format_exc()
        logger.error(f"Error in available-isos: {str(e)}\n{error_tb}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_tb
        }), 500

@bp.route('/available-templates', methods=['GET'])
def available_templates():
    """Get available VM templates for VM creation"""
    if 'user' not in session:
        logger.warning("Unauthorized access attempt to available-templates")
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        logger.info("Fetching available templates")
        api = get_api()
        
        # Get all VMs from cluster
        resources = api.get_request("cluster/resources", {'type': 'vm'})
        
        templates = []
        if resources:
            for vm in resources:
                # Check if VM is tagged as template
                is_template = False
                
                # Check template flag
                if vm.get('template') == 1:
                    is_template = True
                
                # Check tags
                if not is_template and 'tags' in vm:
                    tags = vm.get('tags', '').lower().split(',')
                    if 'template' in tags:
                        is_template = True
                
                if is_template:
                    templates.append({
                        'vmid': vm.get('vmid'),
                        'name': vm.get('name', f"VM {vm.get('vmid')}"),
                        'node': vm.get('node'),
                        'disksize': vm.get('maxdisk', 0),
                        'memory': vm.get('maxmem', 0)
                    })
                    name = vm.get('name', f'VM {vm.get("vmid")}')
                    logger.info(f"Found template: {name} (VMID: {vm.get('vmid')})")
        else:
            logger.warning("Failed to retrieve VM resources")
        
        logger.info(f"Returning {len(templates)} templates")
        return jsonify({
            'success': True,
            'templates': templates
        })
    except Exception as e:
        error_tb = traceback.format_exc()
        logger.error(f"Error in available-templates: {str(e)}\n{error_tb}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_tb
        }), 500
        
@bp.route('/available-storage', methods=['GET'])
def available_storage():
    """Get available storage for VM creation"""
    if 'user' not in session:
        logger.warning("Unauthorized access attempt to available-storage")
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        logger.info("Fetching available storage")
        api = get_api()
        
        # Get storage list from the API
        storage_list = api.get_request("storage")
        
        # Format storage info
        available_storage = []
        if storage_list:
            for storage in storage_list:
                # Check if storage supports VM disks (qemu images)
                if 'content' in storage and any(content_type in storage['content'] for content_type in ['images', 'rootdir']):
                    try:
                        # Get storage details
                        storage_details = api.get_request(f"nodes/{storage.get('node', 'localhost')}/storage/{storage['storage']}/status")
                        
                        if storage_details:
                            available_storage.append({
                                'storage': storage['storage'],
                                'type': storage.get('type', 'unknown'),
                                'total': round(storage_details.get('total', 0) / (1024**3), 2),
                                'used': round(storage_details.get('used', 0) / (1024**3), 2),
                                'avail': round(storage_details.get('avail', 0) / (1024**3), 2)
                            })
                            logger.info(f"Found storage: {storage['storage']} ({storage.get('type', 'unknown')}) - {round(storage_details.get('avail', 0) / (1024**3), 2)}GB free")
                    except Exception as storage_error:
                        logger.error(f"Error getting details for storage {storage['storage']}: {str(storage_error)}")
        else:
            logger.warning("Failed to retrieve storage list")
        
        logger.info(f"Returning {len(available_storage)} storage options")
        return jsonify({
            'success': True,
            'storage': available_storage
        })
    except Exception as e:
        error_tb = traceback.format_exc()
        logger.error(f"Error in available-storage: {str(e)}\n{error_tb}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_tb
        }), 500

@bp.route('/find-best-node', methods=['GET'])
def find_best_node():
    """Find the node with the least consumed memory"""
    if 'user' not in session:
        logger.warning("Unauthorized access attempt to find-best-node")
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        logger.info("Finding node with lowest memory usage")
        nodes = get_node_status()
        
        if not nodes:
            logger.warning("No nodes returned from get_node_status")
            return jsonify({
                'success': False,
                'error': 'No nodes found'
            }), 404
        
        # Filter for online nodes only
        online_nodes = [node for node in nodes if node.get('online', False)]
        
        if not online_nodes:
            logger.warning("No online nodes available")
            return jsonify({
                'success': False,
                'error': 'No online nodes found'
            }), 404
        
        # Find node with least memory usage percentage
        best_node = min(online_nodes, key=lambda x: 
                        x.get('mem', 0) / x.get('maxmem', 1) if x.get('maxmem', 0) > 0 else float('inf'))
        
        memory_percent = round((best_node.get('mem', 0) / best_node.get('maxmem', 1) * 100) 
                               if best_node.get('maxmem', 0) > 0 else 0, 2)
        
        logger.info(f"Selected best node: {best_node.get('node')} with {memory_percent}% memory usage")
        
        return jsonify({
            'success': True,
            'node': {
                'name': best_node.get('node'),
                'mem_used': round(best_node.get('mem', 0) / (1024**3), 2),
                'mem_total': round(best_node.get('maxmem', 0) / (1024**3), 2),
                'mem_percent': memory_percent
            }
        })
    except Exception as e:
        error_tb = traceback.format_exc()
        logger.error(f"Error in find-best-node: {str(e)}\n{error_tb}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_tb
        }), 500

@bp.route('/create', methods=['POST'])
def create_new_vm():
    """Create a new VM from ISO or template"""
    if 'user' not in session:
        logger.warning("Unauthorized access attempt to create VM API")
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.json
        logger.info(f"Received VM creation request: {data}")
        
        creation_type = data.get('creation_type')
        name = data.get('name')
        
        # Validate required fields
        if not name or not creation_type:
            logger.warning("Missing required fields for VM creation")
            return jsonify({
                'success': False,
                'error': 'VM name and creation type are required'
            }), 400
        
        # Find best node if not specified
        node = data.get('node')
        if not node:
            logger.info("No node specified, finding best node")
            nodes = get_node_status()
            online_nodes = [n for n in nodes if n.get('online', False)]
            
            if not online_nodes:
                logger.warning("No online nodes available for VM creation")
                return jsonify({
                    'success': False,
                    'error': 'No online nodes found'
                }), 404
                
            # Find node with least memory usage percentage
            best_node = min(online_nodes, key=lambda x: 
                            x.get('mem', 0) / x.get('maxmem', 1) if x.get('maxmem', 0) > 0 else float('inf'))
            node = best_node.get('node')
            logger.info(f"Selected best node: {node}")
        
        # Create VM based on type
        if creation_type == 'iso':
            logger.info(f"Creating VM from ISO on node {node}")
            result = create_vm(
                node=node,
                name=name,
                cpu_cores=int(data.get('cpu', 1)),
                memory=int(data.get('memory', 512)),
                storage=data.get('storage', ''),
                disk_size=int(data.get('disk_size', 8)),
                iso=data.get('iso', ''),
                vlan=data.get('vlan'),
                start_after_create=data.get('start_after_create', False)
            )
        else:  # template
            logger.info(f"Creating VM from template {data.get('template_vmid')} on node {node}")
            result = create_vm(
                node=node,
                name=name,
                template_vmid=data.get('template_vmid'),
                storage=data.get('storage', ''),
                vlan=data.get('vlan'),
                start_after_create=data.get('start_after_create', False)
            )
        
        logger.info(f"VM creation result: {result}")
        
        if result:
            # Handle different types of successful results
            if isinstance(result, dict) and 'data' in result:
                # If result is a dictionary with a 'data' key
                vmid = result['data']
                logger.info(f"VM created with ID: {vmid}")
                return jsonify({
                    'success': True,
                    'vmid': vmid,
                    'task_id': result.get('task_id')
                })
            elif isinstance(result, str) and result.startswith('UPID:'):
                # If result is a UPID string, extract the VMID from the request
                vmid = int(data.get('vmid', next_vmid) if 'next_vmid' in locals() else 208)
                logger.info(f"VM creation task started with UPID: {result} for VM ID: {vmid}")
                return jsonify({
                    'success': True,
                    'vmid': vmid,
                    'task_id': result
                })
            else:
                # For any other successful result
                logger.info(f"VM creation succeeded with unstructured result: {result}")
                return jsonify({
                    'success': True,
                    'result': str(result) if result else 'Task submitted successfully'
                })
        else:
            error_msg = result.get('error', {}).get('message', 'Unknown error') if isinstance(result, dict) else 'Failed to create VM'
            logger.error(f"VM creation failed: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
    except Exception as e:
        error_tb = traceback.format_exc()
        logger.error(f"Error in create_new_vm: {str(e)}\n{error_tb}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_tb
        }), 500