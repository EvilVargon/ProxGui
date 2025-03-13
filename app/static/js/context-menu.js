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
                e.stopPropagation();
                showContextMenu(e, this.getAttribute('data-id'), 'vm');
            });
        });
        
        // Apply to folder items
        document.querySelectorAll('.folder-item').forEach(folderItem => {
            folderItem.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                e.stopPropagation();
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
                            <div class="form-group mb-3">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <label class="form-label mb-0">Select destination folder:</label>
                                    <button type="button" class="btn btn-sm btn-outline-secondary" id="expandAllFolders">Expand All</button>
                                </div>
                                <div class="folder-tree-container border rounded p-2" style="max-height: 300px; overflow-y: auto;">
                                    <div id="folderTreeView">
                                        <!-- Folder tree will be loaded here -->
                                    </div>
                                </div>
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
        
        // Build folder tree view
        const treeContainer = document.getElementById('folderTreeView');
        treeContainer.innerHTML = '';
        
        // Add root option
        const rootItem = document.createElement('div');
        rootItem.className = 'folder-tree-item';
        rootItem.innerHTML = `
            <div class="form-check">
                <input class="form-check-input" type="radio" name="folderSelection" id="folder-root" value="root" checked>
                <label class="form-check-label" for="folder-root">
                    <i class="fas fa-folder me-1 text-warning"></i> Root
                </label>
            </div>
        `;
        treeContainer.appendChild(rootItem);
        
        // Create a flat list of all folders
        const allFolders = [];
        document.querySelectorAll('.folder-item').forEach(folder => {
            const folderId = folder.getAttribute('data-folder-id');
            const folderName = folder.querySelector('.folder-name').textContent.trim();
            
            // Skip the current folder and its children if we're moving a folder
            if (itemType === 'folder' && folderId === itemId) {
                return;
            }
            
            // Find parent id
            let parentId = 'root';
            const folderContent = folder.closest('.folder-content');
            if (folderContent) {
                parentId = folderContent.getAttribute('data-parent') || 'root';
            }
            
            allFolders.push({
                id: folderId,
                name: folderName,
                parentId: parentId
            });
        });
        
        // Log all folders for debugging
        console.log('All folders:', allFolders);
        
        // Build folder tree
        buildFolderTreeFromList(treeContainer, allFolders, 'root', 0);
        
        // Set up expand all button
        document.getElementById('expandAllFolders').onclick = function() {
            document.querySelectorAll('.folder-tree-children').forEach(child => {
                child.style.display = 'block';
                
                // Update toggle icons
                const toggleIcon = child.previousElementSibling.querySelector('.folder-tree-toggle i');
                if (toggleIcon) {
                    toggleIcon.className = 'fas fa-caret-down';
                }
            });
        };
        
        // Make folder tree radio labels clickable
        document.querySelectorAll('#folderTreeView .form-check-label').forEach(label => {
            label.addEventListener('click', function() {
                const radio = document.getElementById(this.getAttribute('for'));
                if (radio) {
                    radio.checked = true;
                }
            });
        });
        
        // Set up folder toggle clicks
        document.querySelectorAll('.folder-tree-toggle').forEach(toggle => {
            toggle.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const children = this.closest('.folder-tree-item').nextElementSibling;
                if (children && children.classList.contains('folder-tree-children')) {
                    if (children.style.display === 'none') {
                        children.style.display = 'block';
                        this.querySelector('i').className = 'fas fa-caret-down';
                    } else {
                        children.style.display = 'none';
                        this.querySelector('i').className = 'fas fa-caret-right';
                    }
                }
            };
        });
        
        // Set up the confirm button
        document.getElementById('confirmFolderMove').onclick = function() {
            const selectedFolder = document.querySelector('input[name="folderSelection"]:checked');
            if (selectedFolder) {
                const selectedFolderId = selectedFolder.value;
                moveItemToFolder(itemId, itemType, selectedFolderId);
                bootstrap.Modal.getInstance(folderModal).hide();
            } else {
                alert('Please select a destination folder');
            }
        };
        
        // Show the modal
        const modal = new bootstrap.Modal(folderModal);
        modal.show();
    }
    
    // Build folder tree from a flat list of folders
    function buildFolderTreeFromList(container, folders, parentId, level) {
        // Find children of this parent
        const children = folders.filter(folder => folder.parentId === parentId);
        
        if (children.length === 0) return;
        
        // Create container for children if this isn't root
        let childrenContainer = container;
        
        if (parentId !== 'root') {
            childrenContainer = document.createElement('div');
            childrenContainer.className = 'folder-tree-children';
            childrenContainer.style.paddingLeft = '20px';
            
            // Default collapsed for levels > 1
            if (level > 1) {
                childrenContainer.style.display = 'none';
            }
            
            container.appendChild(childrenContainer);
        }
        
        // Add each folder
        children.forEach(folder => {
            // Create folder item
            const folderItem = document.createElement('div');
            folderItem.className = 'folder-tree-item';
            
            // Check if this folder has children
            const hasChildren = folders.some(f => f.parentId === folder.id);
            
            folderItem.innerHTML = `
                <div class="d-flex align-items-center py-1">
                    ${hasChildren ? `<span class="folder-tree-toggle me-1" style="width: 15px; cursor: pointer;"><i class="fas fa-caret-${level > 1 ? 'right' : 'down'}"></i></span>` : '<span style="width: 15px;"></span>'}
                    <div class="form-check mb-0">
                        <input class="form-check-input" type="radio" name="folderSelection" id="folder-${folder.id}" value="${folder.id}">
                        <label class="form-check-label" for="folder-${folder.id}">
                            <i class="fas fa-folder me-1 text-warning"></i> ${folder.name}
                        </label>
                    </div>
                </div>
            `;
            
            childrenContainer.appendChild(folderItem);
            
            // Recursively build children
            if (hasChildren) {
                buildFolderTreeFromList(folderItem, folders, folder.id, level + 1);
            }
        });
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