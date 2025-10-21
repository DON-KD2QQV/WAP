// Function to handle navigation with special case for Weather Alert Pro

function handleNavigation(selectElementId) {
    const el = document.getElementById(selectElementId);
    if (!el) return;
    el.addEventListener('change', function() {
        const selectedValue = this.value;
        if (selectedValue) {
            if (selectedValue === "https://www.radiooperator.net/cgi-bin/weather.cgi") {
                window.open(selectedValue, '_blank', 'noopener');
            } else {
                window.location.href = selectedValue;
            }
            this.selectedIndex = 0; // Reset to default option
        }
    });
}

// Call the function for both navigation and bottom_navigation
handleNavigation('navigation');
handleNavigation('bottom_navigation');
