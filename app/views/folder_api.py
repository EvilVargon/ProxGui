from flask import Blueprint, jsonify, request, session, render_template_string
from app.models.folder import FolderManager
from app.proxmox.api import get_user_vms

bp = Blueprint('folder_api', __name__, url_prefix='/api')

# Initialize folder manager
folder_manager = FolderManager(data_dir='app/data')

@bp.route('/folders', methods=['GET'])
def get_folders():
    """Get all folders"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        folders = folder_manager.get_folders()
        return jsonify({
            'success': True,
            'folders': folders
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/folders', methods=['POST'])
def create_folder():
    """Create a new folder"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    name = data.get('name')
    parent_id = data.get('parent_id', 'root')
    
    if not name:
        return jsonify({
            'success': False,
            'error': 'Folder name is required'
        }), 400
    
    try:
        folder_id = folder_manager.create_folder(name, parent_id)
        return jsonify({
            'success': True,
            'folder_id': folder_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/folders/<folder_id>', methods=['PUT'])
def update_folder(folder_id):
    """Update a folder"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    
    try:
        folder = folder_manager.update_folder(folder_id, data)
        return jsonify({
            'success': True,
            'folder': folder
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/folders/<folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    """Delete a folder"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        result = folder_manager.delete_folder(folder_id)
        return jsonify({
            'success': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/move-item', methods=['POST'])
def move_item():
    """Move a VM or folder to a new parent"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    item_id = data.get('item_id')
    item_type = data.get('item_type')
    parent_id = data.get('parent_id', 'root')
    
    print(f"API: Moving {item_type} {item_id} to parent {parent_id}")
    
    if not item_id or not item_type:
        return jsonify({
            'success': False,
            'error': 'Item ID and type are required'
        }), 400
    
    try:
        if item_type == 'folder':
            # Don't allow moving a folder to itself or a child
            if item_id == parent_id:
                return jsonify({
                    'success': False,
                    'error': 'Cannot move a folder to itself'
                }), 400
            
            # Check for circular reference
            if parent_id != 'root':
                current = folder_manager.get_folder(parent_id)
                while current and current.get('parent_id') != 'root':
                    if current.get('parent_id') == item_id:
                        return jsonify({
                            'success': False,
                            'error': 'Circular reference detected'
                        }), 400
                    current = folder_manager.get_folder(current.get('parent_id'))
            
            # Update folder
            folder_manager.update_folder(item_id, {'parent_id': parent_id})
            print(f"Successfully moved folder {item_id} to {parent_id}")
        elif item_type == 'vm':
            # Move VM to new folder
            folder_manager.set_vm_location(item_id, parent_id)
            print(f"Successfully moved VM {item_id} to {parent_id}")
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid item type'
            }), 400
        
        return jsonify({
            'success': True
        })
    except Exception as e:
        import traceback
        print(f"Error moving item: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/vm-tree', methods=['GET'])
def get_vm_tree():
    """Get VM folder tree as HTML"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        user = session['user']
        vms = get_user_vms(user['username'], user['groups'])
        
        # Get folder structure
        folder_structure = folder_manager.get_folder_structure()
        
        # Build HTML
        html = folder_manager.build_folder_html(folder_structure, folder_structure[1], vms)
        
        return jsonify({
            'success': True,
            'html': html
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500