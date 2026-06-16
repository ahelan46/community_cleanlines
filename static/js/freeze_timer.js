/**
 * Global Inactivity Freeze Timer
 * Monitors user inactivity across dashboards and freezes the session
 * if the attendance state is 'running' and 5 minutes have passed without activity.
 */

(function() {
    const INACTIVITY_LIMIT_MS = 5 * 60 * 1000; // 5 minutes
    let inactivityTimeout = null;
    let activityEventsBound = false;

    // Helper: get CSRF token from cookies
    function getCsrfToken() {
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
        // Double-check the state hasn't changed right before freezing
        if (localStorage.getItem('attendance_freeze_state') !== 'running') {
            return;
        }

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
        
        // Only run timer if user is checked in and not on break
        if (localStorage.getItem('attendance_freeze_state') === 'running') {
            inactivityTimeout = setTimeout(triggerFreeze, INACTIVITY_LIMIT_MS);
        }
    }

    function handleActivity() {
        if (localStorage.getItem('attendance_freeze_state') === 'running') {
            resetInactivityTimer();
        }
    }

    function bindActivityEvents() {
        if (activityEventsBound) return;
        const events = ['mousemove', 'keydown', 'scroll', 'click', 'touchstart'];
        events.forEach(event => {
            window.addEventListener(event, handleActivity);
        });
        activityEventsBound = true;
    }

    // Initialize timer on script load
    bindActivityEvents();
    resetInactivityTimer();

    // Listen to storage changes to start/stop the timer if it changes in another tab
    window.addEventListener('storage', function(e) {
        if (e.key === 'attendance_freeze_state') {
            resetInactivityTimer();
        }
    });
})();
