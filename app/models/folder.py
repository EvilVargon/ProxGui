import os
import json
from flask import current_app
import time

class FolderManager:
    """Manages VM folders and organization"""
    
    def __init__(self, data_dir='data'):
        """Initialize folder manager with data directory"""
        self.data_dir = data_dir
        self.folders_file = os.path.join(data_dir, 'folders.json')
        self.vm_locations_file = os.path.join(data_dir, 'vm_locations.json')
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize files if they don't exist
        if not os.path.exists(self.folders_file):
            self._save_folders({})
        
        if not os.path.exists(self.vm_locations_file):
            self._save_vm_locations({})
    
    def _load_folders(self):
        """Load folders from file"""
        try:
            with open(self.folders_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_folders(self, folders):
        """Save folders to file"""
        with open(self.folders_file, 'w') as f:
            json.dump(folders, f, indent=2)
    
    def _load_vm_locations(self):
        """Load VM locations from file"""
        try:
            with open(self.vm_locations_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_vm_locations(self, vm_locations):
        """Save VM locations to file"""
        with open(self.vm_locations_file, 'w') as f:
            json.dump(vm_locations, f, indent=2)
    
    def get_folders(self):
        """Get all folders"""
        return self._load_folders()
    
    def get_folder(self, folder_id):
        """Get folder by ID"""
        folders = self._load_folders()
        return folders.get(folder_id)
    
    def create_folder(self, name, parent_id='root'):
        """Create a new folder"""
        folders = self._load_folders()
        folder_id = f"folder_{int(time.time())}_{len(folders)}"
        
        # Validate parent exists
        if parent_id != 'root' and parent_id not in folders:
            raise ValueError(f"Parent folder {parent_id} does not exist")
        
        folders[folder_id] = {
            'id': folder_id,
            'name': name,
            'parent_id': parent_id,
            'created_at': time.time()
        }
        
        self._save_folders(folders)
        return folder_id
    
    def update_folder(self, folder_id, data):
        """Update a folder"""
        folders = self._load_folders()
        
        if folder_id not in folders:
            raise ValueError(f"Folder {folder_id} does not exist")
        
        # Only update allowed fields
        for key in ['name', 'parent_id']:
            if key in data:
                folders[folder_id][key] = data[key]
        
        self._save_folders(folders)
        return folders[folder_id]
    
    def delete_folder(self, folder_id):
        """Delete a folder and move its contents to parent"""
        folders = self._load_folders()
        vm_locations = self._load_vm_locations()
        
        if folder_id not in folders:
            raise ValueError(f"Folder {folder_id} does not exist")
        
        # Get parent ID
        parent_id = folders[folder_id]['parent_id']
        
        # Move child folders to parent
        for fid, folder in list(folders.items()):
            if folder['parent_id'] == folder_id:
                folder['parent_id'] = parent_id
        
        # Move VMs to parent
        for vmid, location in vm_locations.items():
            if location == folder_id:
                vm_locations[vmid] = parent_id
        
        # Delete the folder
        del folders[folder_id]
        
        self._save_folders(folders)
        self._save_vm_locations(vm_locations)
        return True
    
    def get_vm_location(self, vmid):
        """Get VM's folder location"""
        vm_locations = self._load_vm_locations()
        return vm_locations.get(str(vmid), 'root')
    
    def set_vm_location(self, vmid, folder_id):
        """Set VM's folder location"""
        folders = self._load_folders()
        vm_locations = self._load_vm_locations()
        
        # Validate folder exists (or is 'root')
        if folder_id != 'root' and folder_id not in folders:
            raise ValueError(f"Folder {folder_id} does not exist")
        
        vm_locations[str(vmid)] = folder_id
        self._save_vm_locations(vm_locations)
        return True
    
    def get_folder_structure(self):
        """
        Get hierarchical folder structure with VMs
        Returns a nested dictionary of the folder structure
        """
        folders = self._load_folders()
        vm_locations = self._load_vm_locations()
        
        # Create structure
        structure = {
            'root': {
                'id': 'root',
                'name': 'Root',
                'children': [],
                'vms': []
            }
        }
        
        # Add all folders to structure
        for folder_id, folder in folders.items():
            structure[folder_id] = {
                'id': folder_id,
                'name': folder['name'],
                'children': [],
                'vms': []
            }
        
        # Build hierarchy
        for folder_id, folder in folders.items():
            parent_id = folder['parent_id']
            if parent_id in structure:
                structure[parent_id]['children'].append(folder_id)
        
        # Sort children by name
        for folder_id in structure:
            if folder_id in folders:
                structure[folder_id]['children'].sort(
                    key=lambda x: folders[x]['name'].lower()
                )
        
        return structure, vm_locations
    
    # Update the build_folder_html method in your FolderManager class

    def build_folder_html(self, folder_structure, vm_locations, vms):
        """
        Build HTML representation of folder structure
        Args:
            folder_structure: Output from get_folder_structure()
            vm_locations: VM location mapping
            vms: List of VM objects with at least id, name, status, and memory properties
        Returns:
            HTML string representing the folder tree
        """
        structure, _ = folder_structure
        
        # Group VMs by folder
        vm_by_folder = {}
        for vm in vms:
            vm_id = str(vm.get('vmid', vm.get('id')))
            folder_id = vm_locations.get(vm_id, 'root')
            
            if folder_id not in vm_by_folder:
                vm_by_folder[folder_id] = []
            
            vm_by_folder[folder_id].append(vm)
        
        # Sort VMs in each folder by name
        for folder_id in vm_by_folder:
            vm_by_folder[folder_id].sort(key=lambda x: x.get('name', '').lower())
        
        # Helper function to recursively build HTML
        def build_folder_html_recursive(folder_id):
            folder = structure[folder_id]
            html = []
            
            # Don't show root folder in HTML
            if folder_id != 'root':
                html.append(f"""
                <div class="folder-item" data-folder-id="{folder_id}" data-id="{folder_id}">
                    <span class="folder-toggle"><i class="fas fa-caret-down"></i></span>
                    <i class="fas fa-folder text-warning"></i>
                    <span class="folder-name">{folder['name']}</span>
                </div>
                """)
            
            # Create folder content div
            content_html = []
            
            # Add child folders
            for child_id in folder['children']:
                content_html.append(build_folder_html_recursive(child_id))
            
            # Add VMs in this folder
            if folder_id in vm_by_folder:
                for vm in vm_by_folder[folder_id]:
                    vm_id = vm.get('vmid', vm.get('id'))
                    vm_name = vm.get('name', f'VM {vm_id}')
                    vm_status = vm.get('status', 'unknown')
                    vm_node = vm.get('node', '')
                    vm_type = vm.get('type', 'qemu')
                    
                    # Calculate memory usage (if available)
                    memory_percent = 0
                    if 'mem' in vm and 'maxmem' in vm and vm['maxmem'] > 0:
                        memory_percent = (vm['mem'] / vm['maxmem']) * 100
                    elif 'memory_usage' in vm:
                        memory_percent = vm['memory_usage']
                    
                    # Status icon
                    status_icon = 'circle'
                    status_class = 'vm-status-off'
                    if vm_status == 'running':
                        status_class = 'vm-status-on'
                    
                    content_html.append(f"""
                    <div class="vm-item" data-id="{vm_id}" data-name="{vm_name}" data-node="{vm_node}" data-type="{vm_type}">
                        <div class="vm-status {status_class}">
                            <i class="fas fa-{status_icon}"></i>
                        </div>
                        <div class="vm-info">
                            <p class="vm-name" title="{vm_name}">{vm_name}</p>
                            <div class="vm-memory-bar">
                                <div class="vm-memory-fill" style="width: {memory_percent}%;"></div>
                            </div>
                        </div>
                        <a href="/vm/{vm_node}/{vm_id}?type={vm_type}" class="vm-link">
                            <i class="fas fa-external-link-alt"></i>
                        </a>
                    </div>
                    """)
            
            # Only add content if not root or if it has content
            if folder_id != 'root' or content_html:
                content_parent = folder_id if folder_id != 'root' else 'root'
                content_class = "" if folder_id == 'root' else "folder-content"
                
                html.append(f"""
                <div class="{content_class}" data-parent="{content_parent}">
                    {"".join(content_html)}
                </div>
                """)
            
            return "".join(html)
        
        # Build from root
        return build_folder_html_recursive('root')