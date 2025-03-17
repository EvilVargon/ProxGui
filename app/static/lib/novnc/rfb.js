// Debug flag - set to true for verbose logging
const DEBUG = true;

// Debug logger function
function debug(...args) {
    if (DEBUG) {
        console.log("[NoVNC Debug]", ...args);
    }
}

// Log that the file loaded
debug("rfb.js loaded");

// Basic RFB implementation for ProxGui
class RFB {
    constructor(target, url, options) {
        debug("RFB constructor called", target, url, options);
        this.target = target;
        this.url = url;
        this.options = options || {};
        this._eventListeners = {};
        
        // Display connection status in canvas
        this._updateCanvas("Connecting to VNC...");
        
        // Try to connect
        this._connect();
    }
    
    // Add event listener
    addEventListener(type, callback) {
        if (!this._eventListeners[type]) {
            this._eventListeners[type] = [];
        }
        this._eventListeners[type].push(callback);
    }
    
    // Fire event
    _fireEvent(type, detail) {
        if (!this._eventListeners[type]) return;
        
        const event = { detail };
        this._eventListeners[type].forEach(callback => callback(event));
    }
    
    // Update canvas with message
    _updateCanvas(message, color = "black", textColor = "white") {
        if (!this.target || !this.target.getContext) return;
        
        const canvas = this.target;
        const ctx = canvas.getContext("2d");
        
        // Clear canvas
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw message
        ctx.font = "16px Arial";
        ctx.fillStyle = textColor;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(message, canvas.width / 2, canvas.height / 2);
    }
    
    // Connect to VNC server
    _connect() {
        try {
            // Create WebSocket connection
            console.log("Connecting to", this.url);
            this._ws = new WebSocket(this.url);
            
            // Setup event handlers
            this._ws.onopen = () => {
                console.log("WebSocket connected");
                this._updateCanvas("Connected to VNC server", "green");
                this._fireEvent("connect", {});
            };
            
            this._ws.onclose = (e) => {
                console.log("WebSocket closed", e);
                this._updateCanvas("Disconnected: " + (e.reason || "Connection closed"));
                this._fireEvent("disconnect", { reason: e.reason || "Connection closed" });
            };
            
            this._ws.onerror = (e) => {
                console.error("WebSocket error", e);
                this._updateCanvas("Connection error", "darkred");
                this._fireEvent("disconnect", { reason: "WebSocket error" });
            };
            
            this._ws.onmessage = (e) => {
                console.log("WebSocket message", e.data);
                // In a real implementation, this would handle VNC protocol messages
            };
        } catch (error) {
            console.error("Failed to connect:", error);
            this._updateCanvas("Connection failed: " + error.message, "darkred");
            this._fireEvent("disconnect", { reason: error.message });
        }
    }
    
    // Disconnect from VNC server
    disconnect() {
        if (this._ws) {
            this._ws.close();
            this._ws = null;
        }
        
        this._updateCanvas("Disconnected by user");
        this._fireEvent("disconnect", { reason: "Disconnected by user" });
    }
    
    // Send Ctrl+Alt+Del
    sendCtrlAltDel() {
        console.log("Sending Ctrl+Alt+Del");
        this._updateCanvas("Sent Ctrl+Alt+Del", "blue");
        // In a real implementation, this would send the key combination
    }
    
    // Resize the session
    resizeSession() {
        console.log("Resizing session");
        // In a real implementation, this would handle resizing
    }
}

// Make RFB available globally
window.RFB = RFB;

// Fire the novnc-ready event immediately
document.addEventListener('DOMContentLoaded', function() {
    console.log("Firing novnc-ready event");
    window.dispatchEvent(new Event('novnc-ready'));
});

// Also fire it now in case the DOM is already loaded
if (document.readyState === "complete" || document.readyState === "interactive") {
    console.log("DOM already loaded, firing novnc-ready event immediately");
    window.dispatchEvent(new Event('novnc-ready'));
}
