// NoVNC bundle for ProxGui
// This file includes the necessary NoVNC dependencies

console.log("[NoVNC Bundle] Loading dependencies");

(function() {
    // Check if RFB is already defined - we don't want to override it
    if (!window.RFB) {
        console.log("[NoVNC Bundle] RFB not yet defined, will check for it from core");
        
        // If rfb.js wasn't loaded directly, we could load it here
        // But we prefer to use the direct script tag approach in console.html
        console.log("[NoVNC Bundle] Using existing RFB implementation if available");
    } else {
        console.log("[NoVNC Bundle] RFB already defined, using existing implementation");
    }
    
    // Signal that NoVNC bundle is ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log("[NoVNC Bundle] DOM loaded, dispatching novnc-ready event");
        window.dispatchEvent(new Event('novnc-ready'));
    });
    
    // Also dispatch now in case DOM is already loaded
    if (document.readyState === "complete" || document.readyState === "interactive") {
        console.log("[NoVNC Bundle] DOM already loaded, dispatching novnc-ready immediately");
        window.dispatchEvent(new Event('novnc-ready'));
    }
})();
