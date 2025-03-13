// Context Menu for VM and Folder Management
document.addEventListener('DOMContentLoaded', function() {
    // Create context menu element
    const contextMenu = document.createElement('div');
    contextMenu.className = 'context-menu';
    contextMenu.style.display = 'none';
    document.body.appendChild(contextMenu);
    
    // Track which item the context menu is for
    let currentItemId = null;
    let currentItemType = null;
    
    // Add event listeners for right-click on VM items
    initContextMenuListeners();
    
    // Close context menu when clicking elsewhere
    document.addEventListener('click', function(e) {
        if (!contextMenu.contains(e.target)) {
            contextMenu.style.display = 'none';
        }
    });
    
    // Handle escape key to close context menu
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            contextMenu.style.display = 'none';
        }
    });
    
    // Initialize context menu listeners
    function initContextMenuListeners() {
        // Apply to VM items
        document.querySelectorAll('.vm-item').forEach(vmItem => {
            vmItem.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                showContextMenu(e, this.getAttribute('data-id'), 'vm');
            });
        });
        
        // Apply to folder items
        document.querySelectorAll('.folder-item').forEach(folderItem => {
            folderItem.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                showContextMenu(e, this.getAttribute('data-folder-id'), 'folder');
            });
        });
    }
    
    // Show context menu
    function showContextMenu(e, itemId, itemType) {
        currentItemId = itemId;
        currentItemType = itemType;
        
        // Position the menu
        contextMenu.style.left = e.pageX + 'px';
        contextMenu.style.top = e.pageY + 'px';
        
        // Clear previous menu items
        contextMenu.innerHTML = '';
        
        // Create menu based on item type
        if (itemType === 'vm') {
            // Menu for VMs
            contextMenu.innerHTML = `
                <div class="context-menu-header">VM Options</div>
                <div class="context-menu-item" id="move-vm-to-folder">Move to folder</div>
                <div class="context-menu-item" id="move-vm-to-root">Move to root</div>
            `;
            
            // Add event listener for move to folder
            document.getElementById('move-vm-to-folder').addEventListener('click', function() {
                showFolderSelectionModal(itemId, 'vm');
                contextMenu.style.display = 'none';
            });
            
            // Add event listener for move to root
            document.getElementById('move-vm-to-root').addEventListener('click', function() {
                moveItemToFolder(itemId, 'vm', 'root');
                contextMenu.style.display = 'none';
            });
        } else if (itemType === 'folder') {
            // Menu for folders
            contextMenu.innerHTML = `
                <div class="context-menu-header">Folder Options</div>
                <div class="context-menu-item" id="rename-folder">Rename folder</div>
                <div class="context-menu-item" id="move-folder-to-folder">Move to another folder</div>
                <div class="context-menu-item" id="move-folder-to-root">Move to root</div>
                <div class="context-menu-separator"></div>
                <div class="context-menu-item item-danger" id="delete-folder">Delete folder</div>
            `;
            
            // Add event listener for rename
            document.getElementById('rename-folder').addEventListener('click', function() {
                showRenameFolderModal(itemId);
                contextMenu.style.display = 'none';
            });
            
            // Add event listener for move to folder
            document.getElementById('move-folder-to-folder').addEventListener('click', function() {
                showFolderSelectionModal(itemId, 'folder');
                contextMenu.style.display = 'none';
            });
            
            // Add event listener for move to root
            document.getElementById('move-folder-to-root').addEventListener('click', function() {
                moveItemToFolder(itemId, 'folder', 'root');
                contextMenu.style.display = 'none';
            });
            
            // Add event listener for delete
            document.getElementById('delete-folder').addEventListener('click', function() {
                if (confirm('Are you sure you want to delete this folder? All items will be moved to the parent folder.')) {
                    deleteFolder(itemId);
                }
                contextMenu.style.display = 'none';
            });
        }
        
        // Display the menu
        contextMenu.style.display = 'block';
    }
    
    // Show folder selection modal
    function showFolderSelectionModal(itemId, itemType) {
        // Create or get the modal
        let folderModal = document.getElementById('folderSelectionModal');
        
        if (!folderModal) {
            // Create modal if it doesn't exist
            folderModal = document.createElement('div');
            folderModal.className = 'modal fade';
            folderModal.id = 'folderSelectionModal';
            folderModal.setAttribute('tabindex', '-1');
            folderModal.setAttribute('aria-hidden', 'true');
            
            folderModal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Select Destination Folder</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="form-group">
                                <label for="destinationFolder">Select folder:</label>
                                <select class="form-select" id="destinationFolder">
                                    <!-- Folders will be loaded here -->
                                </select>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="confirmFolderMove">Move</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(folderModal);
        }
        
        // Load folders into the select
        const select = document.getElementById('destinationFolder');
        select.innerHTML = '';
        
        // Get all folders from the DOM
        document.querySelectorAll('.folder-item').forEach(folder => {
            const folderId = folder.getAttribute('data-folder-id');
            
            // Skip the current folder and its children if we're moving a folder
            if (itemType === 'folder' && (folderId === itemId || isChildFolder(folderId, itemId))) {
                return;
            }
            
            const folderName = folder.querySelector('.folder-name').textContent.trim();
            const option = document.createElement('option');
            option.value = folderId;
            option.text = folderName;
            select.appendChild(option);
        });
        
        // Set up the confirm button
        document.getElementById('confirmFolderMove').onclick = function() {
            const selectedFolderId = document.getElementById('destinationFolder').value;
            moveItemToFolder(itemId, itemType, selectedFolderId);
            bootstrap.Modal.getInstance(folderModal).hide();
        };
        
        // Show the modal
        const modal = new bootstrap.Modal(folderModal);
        modal.show();
    }
    
    // Check if a folder is a child of another folder
    function isChildFolder(folderId, parentId) {
        let currentFolder = document.querySelector(`.folder-content[data-parent="${folderId}"]`);
        if (!currentFolder) return false;
        
        // Check parent relationship
        let parent = currentFolder.getAttribute('data-parent');
        while (parent && parent !== 'root') {
            if (parent === parentId) return true;
            currentFolder = document.querySelector(`.folder-content[data-parent="${parent}"]`);
            if (!currentFolder) break;
            parent = currentFolder.getAttribute('data-parent');
        }
        
        return false;
    }
    
    // Show rename folder modal
    function showRenameFolderModal(folderId) {
        // Get current folder name
        const folderElement = document.querySelector(`.folder-item[data-folder-id="${folderId}"]`);
        const currentName = folderElement.querySelector('.folder-name').textContent.trim();
        
        // Create or get the modal
        let renameModal = document.getElementById('renameFolderModal');
        
        if (!renameModal) {
            // Create modal if it doesn't exist
            renameModal = document.createElement('div');
            renameModal.className = 'modal fade';
            renameModal.id = 'renameFolderModal';
            renameModal.setAttribute('tabindex', '-1');
            renameModal.setAttribute('aria-hidden', 'true');
            
            renameModal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Rename Folder</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="form-group">
                                <label for="newFolderName">New name:</label>
                                <input type="text" class="form-control" id="newFolderName">
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="confirmRename">Rename</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(renameModal);
        }
        
        // Set the current name as the value
        document.getElementById('newFolderName').value = currentName;
        
        // Set up the confirm button
        document.getElementById('confirmRename').onclick = function() {
            const newName = document.getElementById('newFolderName').value;
            if (newName.trim()) {
                renameFolder(folderId, newName);
                bootstrap.Modal.getInstance(renameModal).hide();
            }
        };
        
        // Show the modal
        const modal = new bootstrap.Modal(renameModal);
        modal.show();
    }
    
    // Move item to folder
    function moveItemToFolder(itemId, itemType, folderId) {
        fetch('/api/move-item', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                item_id: itemId,
                item_type: itemType,
                parent_id: folderId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload the VM tree
                loadVMTree();
            } else {
                alert('Failed to move item: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error moving item:', error);
            alert('Error moving item: ' + error);
        });
    }
    
    // Delete folder
    function deleteFolder(folderId) {
        fetch(`/api/folders/${folderId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload the VM tree
                loadVMTree();
            } else {
                alert('Failed to delete folder: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error deleting folder:', error);
            alert('Error deleting folder: ' + error);
        });
    }
    
    // Rename folder
    function renameFolder(folderId, newName) {
        fetch(`/api/folders/${folderId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: newName
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload the VM tree
                loadVMTree();
            } else {
                alert('Failed to rename folder: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error renaming folder:', error);
            alert('Error renaming folder: ' + error);
        });
    }
    
    // Add function to reinitialize context menu listeners after tree reload
    window.initContextMenuAfterLoad = function() {
        initContextMenuListeners();
    };
});