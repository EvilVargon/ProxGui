document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    
    // Check for saved theme preference
    const currentTheme = localStorage.getItem('theme');
    
    // Apply saved theme on page load
    if (currentTheme === 'dark') {
        document.body.classList.add('dark-mode');
        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    } else {
        document.body.classList.remove('dark-mode');
        themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
    }
    
    // Toggle theme when button is clicked
    themeToggle.addEventListener('click', function() {
        if (document.body.classList.contains('dark-mode')) {
            document.body.classList.remove('dark-mode');
            localStorage.setItem('theme', 'light');
            this.innerHTML = '<i class="fas fa-moon"></i>';
        } else {
            document.body.classList.add('dark-mode');
            localStorage.setItem('theme', 'dark');
            this.innerHTML = '<i class="fas fa-sun"></i>';
        }
        
        // Re-render charts if they exist
        updateChartsForTheme();
    });
    
    // Function to update chart colors based on theme
    function updateChartsForTheme() {
        // Update CPU chart if it exists
        if (window.cpuChart) {
            window.cpuChart.update();
        }
        
        // Update memory chart if it exists
        if (window.memChart) {
            window.memChart.update();
        }
    }
});