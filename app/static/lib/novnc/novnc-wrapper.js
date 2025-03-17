// NoVNC Wrapper for ProxGui
// This is a simpler implementation that provides a basic RFB class

// NoVNC wrapper loaded successfully
console.log("NoVNC wrapper loaded");

// Define the RFB class globally
window.RFB = function(target, url, options) {
    this.target = target;
    this.url = url;
    this.options = options || {};
    this._eventListeners = {};
    
    // Connect to VNC
    this._connect();
    
    // Fire a ready event
    window.dispatchEvent(new Event('novnc-ready'));
};

// Event handling
RFB.prototype.addEventListener = function(type, listener) {
    if (!this._eventListeners[type]) {
        this._eventListeners[type] = [];
    }
    this._eventListeners[type].push(listener);
};

RFB.prototype._fireEvent = function(type, detail) {
    if (!this._eventListeners[type]) return;
    
    const event = {
        detail: detail || {}
    };
    
    this._eventListeners[type].forEach(function(listener) {
        listener(event);
    });
};

// Connect to VNC
RFB.prototype._connect = function() {
    console.log("Connecting to VNC", this.url);
    
    // Display connection indicator on canvas
    const canvas = this.target;
    if (canvas && canvas.getContext) {
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'black';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.font = '18px Arial';
        ctx.fillStyle = 'white';
        ctx.textAlign = 'center';
        ctx.fillText('Connecting to VNC server...', canvas.width / 2, canvas.height / 2 - 20);
    }
    
    // Simulate a connection attempt with WebSocket
    try {
        const self = this;
        this.socket = new WebSocket(this.url);
        
        this.socket.onopen = function() {
            console.log("WebSocket connected");
            self._fireEvent('connect', {});
            
            // Draw a connected message
            if (canvas && canvas.getContext) {
                const ctx = canvas.getContext('2d');
                ctx.fillStyle = 'green';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                ctx.font = '18px Arial';
                ctx.fillStyle = 'white';
                ctx.textAlign = 'center';
                ctx.fillText('Connected to VNC server', canvas.width / 2, canvas.height / 2 - 20);
                ctx.fillText('(Simulated display - real VNC implementation needed)', canvas.width / 2, canvas.height / 2 + 20);
            }
        };
        
        this.socket.onclose = function(event) {
            console.log("WebSocket closed", event);
            self._fireEvent('disconnect', {
                reason: event.reason || 'Connection closed'
            });
        };
        
        this.socket.onerror = function(error) {
            console.error("WebSocket error", error);
            self._fireEvent('disconnect', {
                reason: 'WebSocket error'
            });
            
            // Draw an error message
            if (canvas && canvas.getContext) {
                const ctx = canvas.getContext('2d');
                ctx.fillStyle = 'black';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                ctx.font = '18px Arial';
                ctx.fillStyle = 'red';
                ctx.textAlign = 'center';
                ctx.fillText('Error connecting to VNC server', canvas.width / 2, canvas.height / 2 - 20);
                ctx.fillStyle = 'white';
                ctx.fillText('Check console for details', canvas.width / 2, canvas.height / 2 + 20);
            }
        };
        
    } catch (error) {
        console.error("Error creating WebSocket", error);
        this._fireEvent('disconnect', {
            reason: 'Failed to create WebSocket: ' + error.message
        });
    }
};

// Disconnect from VNC
RFB.prototype.disconnect = function() {
    if (this.socket) {
        this.socket.close();
        this.socket = null;
    }
    
    this._fireEvent('disconnect', {
        reason: 'Disconnected by user'
    });
};

// Send Ctrl+Alt+Del to the VM
RFB.prototype.sendCtrlAltDel = function() {
    console.log("Sending Ctrl+Alt+Del");
    // This would need to be implemented to actually send the key combination
};

// Resize the VNC display
RFB.prototype.resizeSession = function() {
    console.log("Resizing VNC session");
    // This would need to be implemented to handle resizing
};

// Signal that NoVNC is ready when the page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log("NoVNC wrapper loaded and ready");
    window.dispatchEvent(new Event('novnc-ready'));
});
