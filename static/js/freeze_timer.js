/**
 * Global Inactivity Freeze Timer
 * Monitors user inactivity across dashboards and freezes the session
 * if the attendance state is 'running' and 5 minutes have passed without activity.
 */

(function() {
    let inactivityTimeout = null;
    let activityEventsBound = false;
    let currentThresholdMinutes = 0;
    let pollingInterval = null;

    // Helper: get CSRF token from cookies or meta tag
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) {
            return meta.getAttribute('content');
        }
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const trimmed = cookie.trim();
            if (trimmed.startsWith(name + '=')) {
                return decodeURIComponent(trimmed.substring(name.length + 1));
            }
        }
        return '';
    }

    function triggerFreeze() {

        fetch('/attendance/freeze-inactivity/', {
            method: 'POST',
            headers: { 
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Optional: show a toast or alert before redirecting
                // Redirect to the frozen page
                window.location.href = '/frozen/';
            }
        })
        .catch(err => console.error('Freeze error:', err));
    }

    function resetInactivityTimer() {
        if (inactivityTimeout) {
            clearTimeout(inactivityTimeout);
        }
        
        // Run timer if a global threshold is set
        if (currentThresholdMinutes > 0) {
            inactivityTimeout = setTimeout(triggerFreeze, currentThresholdMinutes * 60 * 1000);
        }
    }

    function fetchThreshold() {
        fetch('/user-mgmt/get-inactivity-threshold/')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    const newThreshold = parseInt(data.minutes) || 0;
                    if (newThreshold !== currentThresholdMinutes) {
                        currentThresholdMinutes = newThreshold;
                        resetInactivityTimer();
                    }
                }
            })
            .catch(err => console.error('Error fetching threshold:', err));
    }

    function handleActivity() {
        resetInactivityTimer();
    }

    function bindActivityEvents() {
        if (activityEventsBound) return;
        const events = ['mousemove', 'keydown', 'scroll', 'click', 'touchstart'];
        events.forEach(event => {
            window.addEventListener(event, handleActivity);
        });
        activityEventsBound = true;
    }

    // Initialize timer and threshold polling on script load
    bindActivityEvents();
    fetchThreshold(); // fetch immediately
    pollingInterval = setInterval(fetchThreshold, 30000); // Poll every 30 seconds
    resetInactivityTimer();

    // Listen to storage changes to start/stop the timer if it changes in another tab
    window.addEventListener('storage', function(e) {
        if (e.key === 'attendance_freeze_state') {
            resetInactivityTimer();
        }
    });
})();
