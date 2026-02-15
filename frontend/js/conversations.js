/**
 * Conversations view module
 */

import * as api from './api.js';
import * as utils from './utils.js';

/**
 * Render the conversations table
 * @param {Array} conversations - Array of conversation objects
 */
function renderConversations(conversations) {
    const conversationsList = document.getElementById('conversations-list');

    if (!conversations || conversations.length === 0) {
        conversationsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">💬</div>
                <div class="empty-state-text">No conversations found</div>
            </div>
        `;
        return;
    }

    conversationsList.innerHTML = `
        <table class="conversations-table">
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Platform</th>
                    <th>Agent</th>
                    <th>Customer</th>
                    <th>Started</th>
                    <th>Duration</th>
                    <th>Messages</th>
                </tr>
            </thead>
            <tbody>
                ${conversations.map(conv => {
                    const agentName = conv.agent ? conv.agent.name : 'Unknown';
                    const customerName = conv.customer ? conv.customer.name || conv.customer.email || conv.customer.phone : 'Unknown';
                    const duration = conv.duration_seconds ? utils.formatDuration(conv.duration_seconds) : 'Active';

                    return `
                        <tr>
                            <td>
                                <span class="conv-type ${utils.getConversationTypeClass(conv.conversation_type)}">
                                    ${conv.conversation_type.toUpperCase()}
                                </span>
                            </td>
                            <td>
                                <span class="conv-status ${utils.getConversationStatusClass(conv.status)}">
                                    ${conv.status.toUpperCase()}
                                </span>
                            </td>
                            <td>${conv.platform}</td>
                            <td>${agentName}</td>
                            <td>${customerName}</td>
                            <td>${utils.formatDateTime(conv.started_at)}</td>
                            <td>${duration}</td>
                            <td>${conv.message_count || 0}</td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

/**
 * Load and display conversations
 */
export async function loadConversations() {
    try {
        utils.hideError();
        utils.showLoading();

        // Get filter values
        const statusFilter = document.getElementById('conv-status-filter')?.value || '';
        const typeFilter = document.getElementById('conv-type-filter')?.value || '';

        const filters = {
            status: statusFilter,
            type: typeFilter,
            limit: 50,
        };

        const data = await api.getConversations(filters);
        renderConversations(data.conversations);

        utils.updateLastUpdateTime();
    } catch (error) {
        console.error('Failed to load conversations:', error);
        utils.showError('Failed to load conversations. Please try again.');
    } finally {
        utils.hideLoading();
    }
}

/**
 * Initialize conversations view
 */
export function initConversationsView() {
    // Set up refresh button
    const refreshButton = document.getElementById('refresh-conversations');
    if (refreshButton) {
        refreshButton.addEventListener('click', loadConversations);
    }

    // Set up filter change handlers
    const statusFilter = document.getElementById('conv-status-filter');
    const typeFilter = document.getElementById('conv-type-filter');

    if (statusFilter) {
        statusFilter.addEventListener('change', loadConversations);
    }

    if (typeFilter) {
        typeFilter.addEventListener('change', loadConversations);
    }

    // Load conversations on init
    loadConversations();
}
