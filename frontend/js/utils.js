/**
 * Utility functions
 */

/**
 * Format a datetime string to a readable format
 * @param {string} datetime - ISO datetime string
 * @returns {string} - Formatted datetime
 */
export function formatDateTime(datetime) {
    if (!datetime) return 'N/A';

    const date = new Date(datetime);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

/**
 * Format a date to time only
 * @param {string} datetime - ISO datetime string
 * @returns {string} - Formatted time
 */
export function formatTime(datetime) {
    if (!datetime) return 'N/A';

    const date = new Date(datetime);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
    });
}

/**
 * Format duration in seconds to readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} - Formatted duration
 */
export function formatDuration(seconds) {
    if (!seconds) return 'N/A';

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    if (minutes === 0) {
        return `${remainingSeconds}s`;
    }

    return `${minutes}m ${remainingSeconds}s`;
}

/**
 * Get relative time (e.g., "2 minutes ago")
 * @param {string} datetime - ISO datetime string
 * @returns {string} - Relative time
 */
export function getRelativeTime(datetime) {
    if (!datetime) return 'N/A';

    const date = new Date(datetime);
    const now = new Date();
    const diffMs = now - date;
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSeconds < 60) {
        return 'just now';
    } else if (diffMinutes < 60) {
        return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
        return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    } else {
        return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    }
}

/**
 * Show loading indicator
 */
export function showLoading() {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.classList.remove('hidden');
    }
}

/**
 * Hide loading indicator
 */
export function hideLoading() {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.classList.add('hidden');
    }
}

/**
 * Show error message
 * @param {string} message - Error message
 */
export function showError(message) {
    const error = document.getElementById('error');
    if (error) {
        error.textContent = message;
        error.classList.remove('hidden');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            error.classList.add('hidden');
        }, 5000);
    }
}

/**
 * Show success notification
 * @param {string} message - Success message
 */
export function showSuccess(message) {
    // Create or get notification element
    let notification = document.getElementById('success-notification');

    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'success-notification';
        notification.className = 'success-notification';
        document.body.appendChild(notification);
    }

    notification.textContent = message;
    notification.classList.add('show');

    // Hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

/**
 * Hide error message
 */
export function hideError() {
    const error = document.getElementById('error');
    if (error) {
        error.classList.add('hidden');
    }
}

/**
 * Update last update time
 */
export function updateLastUpdateTime() {
    const lastUpdateElement = document.getElementById('last-update-time');
    if (lastUpdateElement) {
        lastUpdateElement.textContent = formatTime(new Date().toISOString());
    }
}

/**
 * Get status badge class for LiveChat status
 * @param {string} status - LiveChat status
 * @returns {string} - CSS class
 */
export function getLiveChatStatusClass(status) {
    if (status === 'accepting_chats') return 'accepting';
    return 'not-accepting';
}

/**
 * Get status badge text for LiveChat status
 * @param {string} status - LiveChat status
 * @returns {string} - Display text
 */
export function getLiveChatStatusText(status) {
    if (status === 'accepting_chats') return 'Accepting Chats';
    return 'Not Accepting';
}

/**
 * Get status badge class for RingCentral presence
 * @param {string} presence - RingCentral presence
 * @returns {string} - CSS class
 */
export function getRingCentralPresenceClass(presence) {
    if (presence === 'Available') return 'available';
    if (presence === 'Busy') return 'busy';
    return 'offline';
}

/**
 * Get conversation type class
 * @param {string} type - Conversation type
 * @returns {string} - CSS class
 */
export function getConversationTypeClass(type) {
    return type.toLowerCase();
}

/**
 * Get conversation status class
 * @param {string} status - Conversation status
 * @returns {string} - CSS class
 */
export function getConversationStatusClass(status) {
    return status.toLowerCase();
}
