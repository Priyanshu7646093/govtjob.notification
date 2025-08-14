// Dark Mode Toggle
document.addEventListener('DOMContentLoaded', function() {
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const darkModeStylesheet = document.createElement('link');
    darkModeStylesheet.rel = 'stylesheet';
    darkModeStylesheet.href = '/static/css/dark-mode.css';
    
    // Check for saved dark mode preference
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    
    // Apply dark mode if enabled
    if (isDarkMode) {
        document.body.classList.add('dark-mode');
        darkModeToggle.innerHTML = '<i class="bi bi-sun"></i>';
    }
    
    // Toggle dark mode
    darkModeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        const isNowDark = document.body.classList.contains('dark-mode');
        
        // Update button icon
        darkModeToggle.innerHTML = isNowDark ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon"></i>';
        
        // Save preference
        localStorage.setItem('darkMode', isNowDark);
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Add confirmation dialogs for approve/reject actions
document.querySelectorAll('.approve-form').forEach(form => {
    form.addEventListener('submit', function(e) {
        if (!confirm('Are you sure you want to approve this suggestion?')) {
            e.preventDefault();
        }
    });
});

document.querySelectorAll('.reject-form').then(form => {
    form.addEventListener('submit', function(e) {
        if (!confirm('Are you sure you want to reject this suggestion?')) {
            e.preventDefault();
        }
    });
});