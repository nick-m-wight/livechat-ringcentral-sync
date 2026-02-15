/**
 * API client for backend communication
 */

const API_BASE = '/api';

/**
 * Make a GET request to the API
 * @param {string} endpoint - API endpoint
 * @param {object} params - Query parameters
 * @returns {Promise<object>} - Response data
 */
async function get(endpoint, params = {}) {
    const url = new URL(`${window.location.origin}${API_BASE}${endpoint}`);

    // Add query parameters
    Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
            url.searchParams.append(key, params[key]);
        }
    });

    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
    }

    return await response.json();
}

/**
 * Get all agents with current status
 * @returns {Promise<object>} - Agents data
 */
export async function getAgents() {
    return await get('/agents');
}

/**
 * Get a single agent by ID
 * @param {number} agentId - Agent ID
 * @returns {Promise<object>} - Agent data
 */
export async function getAgent(agentId) {
    return await get(`/agents/${agentId}`);
}

/**
 * Get conversations with optional filters
 * @param {object} filters - Filter options
 * @returns {Promise<object>} - Conversations data
 */
export async function getConversations(filters = {}) {
    return await get('/conversations', filters);
}

/**
 * Get conversation messages
 * @param {number} conversationId - Conversation ID
 * @returns {Promise<object>} - Conversation with messages
 */
export async function getConversationMessages(conversationId) {
    return await get(`/conversations/${conversationId}/messages`);
}

/**
 * Get sync logs with optional filters
 * @param {object} filters - Filter options
 * @returns {Promise<object>} - Sync logs data
 */
export async function getSyncLogs(filters = {}) {
    return await get('/sync-logs', filters);
}

/**
 * Get dashboard statistics
 * @returns {Promise<object>} - Stats data
 */
export async function getStats() {
    return await get('/stats');
}
