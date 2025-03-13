document.addEventListener('DOMContentLoaded', function() {
    // Initialize folder toggle functionality
    initFolderToggles();
    
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

    // Initialize click handlers for VM items
    initVMClickHandlers();
});

// Initialize folder toggles
function initFolderToggles() {
    // Make entire folder item clickable to toggle folders
    document.querySelectorAll('.folder-item').forEach(folderItem => {
        folderItem.addEventListener('click', function(e) {
            // If clicking the toggle icon, let the original handler work
            if (e.target.closest('.folder-toggle')) {
                return;
            }
            
            // Otherwise, find and click the toggle
            const toggle = this.querySelector('.folder-toggle');
            if (toggle) {
                // Create and dispatch a new click event on the toggle
                const clickEvent = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                toggle.dispatchEvent(clickEvent);
            }
        });
    });

    // Still keep original toggle functionality
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

// Initialize click handlers for VM items
function initVMClickHandlers() {
    // Make the entire VM item clickable
    document.querySelectorAll('.vm-item').forEach(vmItem => {
        vmItem.addEventListener('click', function(e) {
            // Don't trigger if clicking the link icon
            if (e.target.closest('.vm-link')) {
                return;
            }
            
            // Navigate to VM details
            const node = this.getAttribute('data-node');
            const vmid = this.getAttribute('data-id');
            const type = this.getAttribute('data-type');
            
            window.location.href = `/vm/${node}/${vmid}?type=${type}`;
        });
    });
}

// Load VM tree via AJAX
function loadVMTree() {
    fetch('/api/vm-tree')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('vm-folder-tree').innerHTML = data.html;
                // Initialize needed functionality
                initFolderToggles();
                initVMClickHandlers();
                
                // Initialize context menu if available
                if (window.initContextMenuAfterLoad) {
                    window.initContextMenuAfterLoad();
                }
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
            
            // Reset the form
            document.getElementById('folderName').value = '';
            
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

// Make loadVMTree globally available so it can be called from context-menu.js
window.loadVMTree = loadVMTree;