/**
 * VM Creation functionality
 * This script handles VM creation via ISO or Template
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("VM Creation JS loaded");
    
    // Initialize the VM creation modal when it's shown
    const createVmModal = document.getElementById('createVmModal');
    if (createVmModal) {
        createVmModal.addEventListener('show.bs.modal', function() {
            console.log("VM creation modal is being shown");
            initVmCreationForm();
        });
    } else {
        console.error("createVmModal element not found");
    }
    
    // Initialize the create VM button
    const createVmBtn = document.getElementById('createVmBtn');
    if (createVmBtn) {
        createVmBtn.addEventListener('click', function() {
            createNewVM();
        });
    } else {
        console.error("createVmBtn element not found");
    }
    
    // Add event listeners for creation type radio buttons
    const typeIso = document.getElementById('typeIso');
    const typeTemplate = document.getElementById('typeTemplate');
    
    if (typeIso) {
        typeIso.addEventListener('click', function() {
            console.log("ISO radio clicked");
            toggleCreationOptions('iso');
        });
    } else {
        console.error("typeIso radio button not found");
    }
    
    if (typeTemplate) {
        typeTemplate.addEventListener('click', function() {
            console.log("Template radio clicked");
            toggleCreationOptions('template');
        });
    } else {
        console.error("typeTemplate radio button not found");
    }
});

// Initialize the VM creation form
function initVmCreationForm() {
    console.log("Initializing VM creation form");
    
    // Find best node for VM creation
    findBestNode();
    
    // Load available ISOs
    loadAvailableISOs();
    
    // Load available templates
    loadAvailableTemplates();
    
    // Load available storage
    loadAvailableStorage();
    
    // Set default values
    const vmNameField = document.getElementById('vmName');
    if (vmNameField) {
        vmNameField.value = `VM-${generateRandomString(6)}`;
    }
    
    // Show ISO options by default
    toggleCreationOptions('iso');
}

// Toggle between ISO and Template creation options
function toggleCreationOptions(creationType) {
    console.log("Toggling creation options to:", creationType);
    
    const isoOptions = document.getElementById('isoOptions');
    const templateOptions = document.getElementById('templateOptions');
    
    if (!isoOptions || !templateOptions) {
        console.error("isoOptions or templateOptions elements not found");
        return;
    }
    
    if (creationType === 'iso') {
        isoOptions.style.display = 'block';
        templateOptions.style.display = 'none';
    } else {
        isoOptions.style.display = 'none';
        templateOptions.style.display = 'block';
    }
}

// Load available ISO images
function loadAvailableISOs() {
    console.log("Loading available ISOs");
    
    const isoSelect = document.getElementById('isoImage');
    if (!isoSelect) {
        console.error("isoImage select element not found");
        return;
    }
    
    isoSelect.innerHTML = '<option value="">Loading ISOs...</option>';
    
    fetch('/api/vm/available-isos')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("ISOs data received:", data);
            
            if (data.success && data.isos?.length > 0) {
                // Sort ISOs by name
                data.isos.sort((a, b) => a.name.localeCompare(b.name));
                
                isoSelect.innerHTML = '<option value="">Select an ISO image</option>';
                data.isos.forEach(iso => {
                    const option = document.createElement('option');
                    option.value = iso.volid;
                    
                    // Format size as GB or MB
                    let sizeDisplay = '';
                    if (iso.size > 1024 * 1024 * 1024) {
                        sizeDisplay = ` (${(iso.size / (1024 * 1024 * 1024)).toFixed(2)} GB)`;
                    } else if (iso.size > 0) {
                        sizeDisplay = ` (${(iso.size / (1024 * 1024)).toFixed(2)} MB)`;
                    }
                    
                    option.textContent = `${iso.name}${sizeDisplay}`;
                    isoSelect.appendChild(option);
                });
            } else {
                isoSelect.innerHTML = '<option value="">No ISO images available</option>';
            }
        })
        .catch(error => {
            console.error('Error loading ISOs:', error);
            isoSelect.innerHTML = '<option value="">Error loading ISO images</option>';
        });
}

// Load available VM templates
function loadAvailableTemplates() {
    console.log("Loading available templates");
    
    const templateSelect = document.getElementById('vmTemplate');
    if (!templateSelect) {
        console.error("vmTemplate select element not found");
        return;
    }
    
    templateSelect.innerHTML = '<option value="">Loading templates...</option>';
    
    fetch('/api/vm/available-templates')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Templates data received:", data);
            
            if (data.success && data.templates?.length > 0) {
                // Sort templates by name
                data.templates.sort((a, b) => a.name.localeCompare(b.name));
                
                templateSelect.innerHTML = '<option value="">Select a template</option>';
                data.templates.forEach(template => {
                    const option = document.createElement('option');
                    option.value = template.vmid;
                    
                    // Format memory as GB
                    let memDisplay = '';
                    if (template.memory > 0) {
                        memDisplay = ` - ${(template.memory / (1024 * 1024 * 1024)).toFixed(2)} GB RAM`;
                    }
                    
                    // Format disk size as GB
                    let diskDisplay = '';
                    if (template.disksize > 0) {
                        diskDisplay = ` - ${(template.disksize / (1024 * 1024 * 1024)).toFixed(2)} GB Disk`;
                    }
                    
                    option.textContent = `${template.name} (${template.vmid})${memDisplay}${diskDisplay}`;
                    templateSelect.appendChild(option);
                });
            } else {
                templateSelect.innerHTML = '<option value="">No templates available</option>';
            }
        })
        .catch(error => {
            console.error('Error loading templates:', error);
            templateSelect.innerHTML = '<option value="">Error loading templates</option>';
        });
}

// Load available storage
function loadAvailableStorage() {
    console.log("Loading available storage");
    
    const storageSelect = document.getElementById('storage');
    const templateStorageSelect = document.getElementById('templateStorage');
    
    if (!storageSelect || !templateStorageSelect) {
        console.error("Storage select elements not found");
        return;
    }
    
    storageSelect.innerHTML = '<option value="">Loading storage options...</option>';
    templateStorageSelect.innerHTML = '<option value="">Use source storage</option>';
    
    fetch('/api/vm/available-storage')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Storage data received:", data);
            
            if (data.success && data.storage?.length > 0) {
                // Sort storage by name
                data.storage.sort((a, b) => a.storage.localeCompare(b.storage));
                
                storageSelect.innerHTML = '';
                templateStorageSelect.innerHTML = '<option value="">Use source storage</option>';
                
                data.storage.forEach(storage => {
                    // Add to main storage select
                    const option1 = document.createElement('option');
                    option1.value = storage.storage;
                    option1.textContent = `${storage.storage} (${storage.avail} GB free of ${storage.total} GB)`;
                    storageSelect.appendChild(option1);
                    
                    // Add to template storage select
                    const option2 = document.createElement('option');
                    option2.value = storage.storage;
                    option2.textContent = `${storage.storage} (${storage.avail} GB free of ${storage.total} GB)`;
                    templateStorageSelect.appendChild(option2);
                });
                
                // Select the first option in the main storage select
                if (storageSelect.options.length > 0) {
                    storageSelect.selectedIndex = 0;
                }
            } else {
                storageSelect.innerHTML = '<option value="">No storage available</option>';
                templateStorageSelect.innerHTML = '<option value="">Use source storage</option>';
            }
        })
        .catch(error => {
            console.error('Error loading storage:', error);
            storageSelect.innerHTML = `<option value="">Error loading storage: ${error.message}</option>`;
            templateStorageSelect.innerHTML = '<option value="">Use source storage</option>';
        });
}

// Find the best node for VM creation
function findBestNode() {
    console.log("Finding best node");
    
    const bestNodeInfo = document.getElementById('bestNodeInfo');
    if (!bestNodeInfo) {
        console.error("bestNodeInfo element not found");
        return;
    }
    
    bestNodeInfo.innerHTML = `
        <div class="spinner-border spinner-border-sm" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        Checking available nodes...
    `;
    
    fetch('/api/vm/find-best-node')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Best node data received:", data);
            
            if (data.success && data.node) {
                bestNodeInfo.innerHTML = `
                    <strong>Selected Node:</strong> ${data.node.name} 
                    (Memory: ${data.node.mem_used} GB / ${data.node.mem_total} GB, ${data.node.mem_percent}% used)
                `;
                // Store the node name for later use
                bestNodeInfo.dataset.nodeName = data.node.name;
            } else {
                bestNodeInfo.innerHTML = `
                    <span class="text-danger">Error: ${data.error || 'No suitable node found'}</span>
                `;
            }
        })
        .catch(error => {
            console.error('Error finding best node:', error);
            bestNodeInfo.innerHTML = `
                <span class="text-danger">Error checking nodes: ${error.message}</span>
            `;
        });
}

// Create a new VM with the current form settings
function createNewVM() {
    console.log("Creating new VM");
    
    // Get form values
    const creationTypeEl = document.querySelector('input[name="creationType"]:checked');
    if (!creationTypeEl) {
        alert('Please select a creation method');
        return;
    }
    
    const creationType = creationTypeEl.value;
    const vmNameEl = document.getElementById('vmName');
    const vmVlanEl = document.getElementById('vmVlan');
    const startAfterCreateEl = document.getElementById('startAfterCreate');
    
    if (!vmNameEl || !vmVlanEl || !startAfterCreateEl) {
        console.error("Required form elements not found");
        return;
    }
    
    const vmName = vmNameEl.value;
    const vmVlan = vmVlanEl.value;
    const startAfterCreate = startAfterCreateEl.checked;
    
    // Get best node from the stored data attribute
    const bestNodeInfo = document.getElementById('bestNodeInfo');
    if (!bestNodeInfo) {
        console.error("bestNodeInfo element not found");
        return;
    }
    
    const nodeName = bestNodeInfo.dataset.nodeName;
    
    // Validate form
    if (!vmName.trim()) {
        alert('Please enter a VM name');
        return;
    }
    
    if (!nodeName) {
        alert('No suitable node found for VM creation');
        return;
    }
    
    // Prepare data based on creation type
    let requestData = {
        creation_type: creationType,
        name: vmName,
        node: nodeName,
        vlan: vmVlan || null,
        start_after_create: startAfterCreate
    };
    
    if (creationType === 'iso') {
        // Get ISO-specific values
        const isoImageEl = document.getElementById('isoImage');
        const storageEl = document.getElementById('storage');
        const vmCpuEl = document.getElementById('vmCpu');
        const vmMemoryEl = document.getElementById('vmMemory');
        const vmDiskEl = document.getElementById('vmDisk');
        
        if (!isoImageEl || !storageEl || !vmCpuEl || !vmMemoryEl || !vmDiskEl) {
            console.error("ISO form elements not found");
            return;
        }
        
        const isoImage = isoImageEl.value;
        const storage = storageEl.value;
        const vmCpu = parseInt(vmCpuEl.value);
        const vmMemory = parseInt(vmMemoryEl.value);
        const vmDisk = parseInt(vmDiskEl.value);
        
        // Validate ISO form
        if (!isoImage) {
            alert('Please select an ISO image');
            return;
        }
        
        if (!storage) {
            alert('Please select a storage location');
            return;
        }
        
        // Add ISO-specific data
        requestData = {
            ...requestData,
            iso: isoImage,
            storage: storage,
            cpu: vmCpu,
            memory: vmMemory,
            disk_size: vmDisk
        };
    } else {
        // Get template-specific values
        const templateIdEl = document.getElementById('vmTemplate');
        const templateStorageEl = document.getElementById('templateStorage');
        
        if (!templateIdEl || !templateStorageEl) {
            console.error("Template form elements not found");
            return;
        }
        
        const templateId = templateIdEl.value;
        const templateStorage = templateStorageEl.value;
        
        // Validate template form
        if (!templateId) {
            alert('Please select a template');
            return;
        }
        
        // Add template-specific data
        requestData = {
            ...requestData,
            template_vmid: templateId,
            storage: templateStorage || null
        };
    }
    
    // Disable create button and show loading state
    const createButton = document.getElementById('createVmBtn');
    if (!createButton) {
        console.error("createVmBtn element not found");
        return;
    }
    
    createButton.disabled = true;
    createButton.innerHTML = `
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        Creating VM...
    `;
    
    console.log("Sending VM creation request:", requestData);
    
    // Send creation request
    fetch('/api/vm/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || `HTTP error! Status: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log("VM creation response:", data);
        
        if (data.success) {
            // Hide modal
            const modalElement = document.getElementById('createVmModal');
            if (modalElement) {
                const modalInstance = bootstrap.Modal.getInstance(modalElement);
                if (modalInstance) {
                    modalInstance.hide();
                } else {
                    console.error("Modal instance not found");
                }
            }
            
            // Show appropriate success message based on response data
            if (data.vmid) {
                alert(`VM created successfully with ID: ${data.vmid}`);
            } else if (data.task_id) {
                alert(`VM creation task started. The VM will be available shortly.`);
            } else {
                alert(`VM creation task submitted successfully.`);
            }
            
            // Reload the page to show the new VM or to refresh for pending creation
            window.location.reload();
        } else {
            // Show error message
            alert(`Failed to create VM: ${data.error || 'Unknown error'}`);
            
            // Re-enable create button
            createButton.disabled = false;
            createButton.textContent = 'Create VM';
        }
    })
    .catch(error => {
        console.error('Error creating VM:', error);
        alert(`Error creating VM: ${error.message}`);
        
        // Re-enable create button
        createButton.disabled = false;
        createButton.textContent = 'Create VM';
    });
}

// Generate a random string for default VM names
function generateRandomString(length) {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    
    return result;
}