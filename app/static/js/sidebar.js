document.addEventListener('DOMContentLoaded', function() {
    // Initialize folder toggle functionality
    initFolderToggles();
    
    // Initialize drag and drop for VMs and folders
    initDragAndDrop();
    
    // Initialize new folder button
    document.getElementById('newFolderBtn')?.addEventListener('click', function() {
        loadFolderOptions();
        const newFolderModal = new bootstrap.Modal(document.getElementById('newFolderModal'));
        newFolderModal.show();
    });
    
    // Initialize create folder button
    document.getElementById('createFolderBtn')?.addEventListener('click', function() {
        createNewFolder();
    });
    
    // Initialize search functionality
    document.getElementById('searchVMs')?.addEventListener('input', function() {
        searchVMs(this.value);
    });
    
    // Load VM tree if not already loaded
    if (document.querySelector('#vm-folder-tree .loading-spinner')) {
        loadVMTree();
    }
});

// Initialize folder toggles
function initFolderToggles() {
    document.querySelectorAll('.folder-toggle').forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const folderItem = this.closest('.folder-item');
            const folderId = folderItem.getAttribute('data-folder-id');
            const folderContent = document.querySelector(`.folder-content[data-parent="${folderId}"]`);
            
            if (folderContent) {
                if (folderContent.style.display === 'none') {
                    folderContent.style.display = 'block';
                    this.innerHTML = '<i class="fas fa-caret-down"></i>';
                    // Store state in localStorage
                    localStorage.setItem(`folder_${folderId}_open`, 'true');
                } else {
                    folderContent.style.display = 'none';
                    this.innerHTML = '<i class="fas fa-caret-right"></i>';
                    // Store state in localStorage
                    localStorage.setItem(`folder_${folderId}_open`, 'false');
                }
            }
        });
    });
    
    // Make folder name also toggle the folder
    document.querySelectorAll('.folder-name').forEach(name => {
        name.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const folderItem = this.closest('.folder-item');
            const toggle = folderItem.querySelector('.folder-toggle');
            if (toggle) {
                toggle.click();
            }
        });
    });
    
    // Restore folder open states from localStorage
    document.querySelectorAll('.folder-item').forEach(folder => {
        const folderId = folder.getAttribute('data-folder-id');
        const folderContent = document.querySelector(`.folder-content[data-parent="${folderId}"]`);
        const toggle = folder.querySelector('.folder-toggle');
        
        if (folderContent && toggle) {
            const isOpen = localStorage.getItem(`folder_${folderId}_open`) !== 'false';
            
            if (!isOpen) {
                folderContent.style.display = 'none';
                toggle.innerHTML = '<i class="fas fa-caret-right"></i>';
            } else {
                folderContent.style.display = 'block';
                toggle.innerHTML = '<i class="fas fa-caret-down"></i>';
            }
        }
    });
}

// Initialize drag and drop functionality
function initDragAndDrop() {
    console.log("Initializing drag and drop");
    
    // First, apply Sortable to all folder contents
    document.querySelectorAll('.folder-content').forEach(folderContent => {
        console.log("Setting up Sortable for folder content", folderContent.getAttribute('data-parent'));
        
        new Sortable(folderContent, {
            group: 'vm-folders',
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            // Only drag the specific items, not the whole container
            draggable: '.vm-item, .folder-item',
            onStart: function(evt) {
                console.log("Drag started", evt.item.getAttribute('data-id'));
            },
            onEnd: function(evt) {
                console.log("Drag ended", evt.item.getAttribute('data-id'));
                
                const itemId = evt.item.getAttribute('data-id');
                const itemType = evt.item.classList.contains('folder-item') ? 'folder' : 'vm';
                const newParentId = evt.to.getAttribute('data-parent');
                
                // Only update if it actually moved
                if (evt.from !== evt.to || evt.oldIndex !== evt.newIndex) {
                    console.log(`Moving ${itemType} ${itemId} to ${newParentId}`);
                    updateItemParent(itemId, itemType, newParentId);
                }
            }
        });
    });
    
    // Also apply Sortable to the root container
    const rootContainer = document.getElementById('vm-folder-tree');
    if (rootContainer) {
        console.log("Setting up Sortable for root container");
        
        new Sortable(rootContainer, {
            group: 'vm-folders',
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            // Only drag the specific items, not the whole container
            draggable: '.vm-item, .folder-item',
            onStart: function(evt) {
                console.log("Root drag started", evt.item.getAttribute('data-id'));
            },
            onEnd: function(evt) {
                console.log("Root drag ended", evt.item.getAttribute('data-id'));
                
                const itemId = evt.item.getAttribute('data-id');
                const itemType = evt.item.classList.contains('folder-item') ? 'folder' : 'vm';
                
                // Only update if it actually moved
                if (evt.from !== evt.to || evt.oldIndex !== evt.newIndex) {
                    console.log(`Moving ${itemType} ${itemId} to root`);
                    updateItemParent(itemId, itemType, 'root');
                }
            }
        });
    }
    
    // Handle click events on VM items separately
    document.querySelectorAll('.vm-item').forEach(vmItem => {
        vmItem.addEventListener('click', function(e) {
            // If clicking the link icon, let the default action happen
            if (e.target.closest('.vm-link')) {
                return;
            }
            
            // Otherwise navigate manually
            e.preventDefault();
            const node = this.getAttribute('data-node');
            const vmid = this.getAttribute('data-id');
            const type = this.getAttribute('data-type');
            
            window.location.href = `/vm/${node}/${vmid}?type=${type}`;
        });
    });
}

// Update item parent after drag and drop
function updateItemParent(itemId, itemType, parentId) {
    fetch('/api/move-item', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            item_id: itemId,
            item_type: itemType,
            parent_id: parentId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error('Failed to update item parent:', data.error);
            alert('Failed to move item: ' + data.error);
        } else {
            console.log('Successfully moved item');
        }
    })
    .catch(error => {
        console.error('Error updating item parent:', error);
        alert('Error moving item: ' + error);
    });
}

// Load VM tree via AJAX
function loadVMTree() {
    fetch('/api/vm-tree')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('vm-folder-tree').innerHTML = data.html;
                initFolderToggles();
                initDragAndDrop();
            } else {
                document.getElementById('vm-folder-tree').innerHTML = 
                    `<div class="alert alert-danger">Failed to load VM tree: ${data.error}</div>`;
            }
        })
        .catch(error => {
            document.getElementById('vm-folder-tree').innerHTML = 
                `<div class="alert alert-danger">Error loading VM tree: ${error}</div>`;
        });
}

// Load folder options for new folder modal
function loadFolderOptions() {
    const select = document.getElementById('parentFolder');
    
    // Clear existing options except root
    while (select.options.length > 1) {
        select.remove(1);
    }
    
    // Get all folders from the DOM
    document.querySelectorAll('.folder-item').forEach(folder => {
        const folderId = folder.getAttribute('data-folder-id');
        const folderName = folder.querySelector('.folder-name').textContent.trim();
        const option = document.createElement('option');
        option.value = folderId;
        option.text = folderName;
        select.appendChild(option);
    });
}

// Create new folder
function createNewFolder() {
    const folderName = document.getElementById('folderName').value;
    const parentId = document.getElementById('parentFolder').value;
    
    if (!folderName.trim()) {
        alert('Please enter a folder name');
        return;
    }
    
    fetch('/api/folders', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: folderName,
            parent_id: parentId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('newFolderModal')).hide();
            
            // Reload VM tree
            loadVMTree();
        } else {
            alert('Failed to create folder: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        alert('Error creating folder: ' + error);
    });
}

// Search VMs in the sidebar
function searchVMs(query) {
    query = query.toLowerCase();
    
    // Show/hide VMs based on search
    document.querySelectorAll('.vm-item').forEach(vm => {
        const vmName = vm.querySelector('.vm-name').textContent.toLowerCase();
        
        if (query === '' || vmName.includes(query)) {
            vm.style.display = '';
        } else {
            vm.style.display = 'none';
        }
    });
    
    // Show all folders during search (easier to see results)
    if (query) {
        document.querySelectorAll('.folder-content').forEach(folder => {
            folder.style.display = 'block';
        });
        
        document.querySelectorAll('.folder-toggle').forEach(toggle => {
            toggle.innerHTML = '<i class="fas fa-caret-down"></i>';
        });
    } else {
        // Restore saved folder states when search is cleared
        document.querySelectorAll('.folder-item').forEach(folder => {
            const folderId = folder.getAttribute('data-folder-id');
            const folderContent = document.querySelector(`.folder-content[data-parent="${folderId}"]`);
            const toggle = folder.querySelector('.folder-toggle');
            
            if (folderContent && toggle) {
                const isOpen = localStorage.getItem(`folder_${folderId}_open`) !== 'false';
                
                if (!isOpen) {
                    folderContent.style.display = 'none';
                    toggle.innerHTML = '<i class="fas fa-caret-right"></i>';
                }
            }
        });
    }
}