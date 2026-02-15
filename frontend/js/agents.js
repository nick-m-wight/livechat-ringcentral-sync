/**
 * Agents view module with integrated demo controls
 */

import * as api from './api.js';
import * as utils from './utils.js';

// Track active conversations per agent
const activeConversations = new Map(); // agentId -> { chatId?, callId? }

/**
 * Send LiveChat webhook
 */
async function sendLiveChatWebhook(action, payload) {
    const endpoints = {
        'incoming_chat': '/webhooks/livechat/incoming_chat',
        'chat_deactivated': '/webhooks/livechat/chat_deactivated',
    };

    const url = endpoints[action];
    if (!url) {
        throw new Error(`Unknown action: ${action}`);
    }

    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
    }

    return await response.json();
}

/**
 * Send RingCentral webhook
 */
async function sendRingCentralWebhook(payload) {
    const response = await fetch('/webhooks/ringcentral/telephony-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
    }

    return await response.json();
}

/**
 * Start chat for agent
 */
async function startChat(agent) {
    const chatId = `demo_chat_${Date.now()}`;

    const payload = {
        webhook_id: `webhook_${Date.now()}`,
        action: 'incoming_chat',
        payload: {
            chat: {
                id: chatId,
                users: [
                    {
                        id: agent.livechat_agent_id,
                        type: 'agent',
                        email: agent.email,
                        name: agent.name
                    },
                    {
                        id: 'customer_demo',
                        type: 'customer',
                        email: 'customer@demo.com',
                        name: 'Demo Customer'
                    }
                ],
                thread: { active: true }
            }
        }
    };

    try {
        await sendLiveChatWebhook('incoming_chat', payload);
        activeConversations.set(agent.id, {
            ...(activeConversations.get(agent.id) || {}),
            chatId,
            chatAgentId: agent.livechat_agent_id,
            chatAgentName: agent.name
        });

        utils.showSuccess(`Started chat for ${agent.name}`);
        setTimeout(() => loadAgents(), 5000);
    } catch (error) {
        console.error('Failed to start chat:', error);
        utils.showError(`Failed to start chat: ${error.message}`);
    }
}

/**
 * End chat for agent
 */
async function endChat(agent) {
    const conversation = activeConversations.get(agent.id);
    if (!conversation || !conversation.chatId) {
        utils.showError('No active chat for this agent');
        return;
    }

    const payload = {
        webhook_id: `webhook_${Date.now()}`,
        action: 'chat_deactivated',
        payload: {
            chat: {
                id: conversation.chatId,
                users: [
                    {
                        id: agent.livechat_agent_id,
                        type: 'agent',
                        name: agent.name
                    }
                ]
            }
        }
    };

    try {
        await sendLiveChatWebhook('chat_deactivated', payload);

        const updated = activeConversations.get(agent.id);
        delete updated.chatId;
        delete updated.chatAgentId;
        delete updated.chatAgentName;
        if (Object.keys(updated).length === 0) {
            activeConversations.delete(agent.id);
        } else {
            activeConversations.set(agent.id, updated);
        }

        utils.showSuccess(`Ended chat for ${agent.name}`);
        setTimeout(() => loadAgents(), 5000);
    } catch (error) {
        console.error('Failed to end chat:', error);
        utils.showError(`Failed to end chat: ${error.message}`);
    }
}

/**
 * Start call for agent
 */
async function startCall(agent) {
    const sessionId = `demo_session_${Date.now()}`;

    const payload = {
        uuid: `webhook_${Date.now()}`,
        event: `/restapi/v1.0/account/~/extension/${agent.ringcentral_extension_id}/telephony/sessions`,
        timestamp: new Date().toISOString(),
        body: {
            sessionId: sessionId,
            extensionId: agent.ringcentral_extension_id,
            parties: [
                {
                    extensionId: agent.ringcentral_extension_id,
                    status: { code: 'Answered' },
                    direction: 'Inbound',
                    from: { phoneNumber: '+15550001234' },
                    to: { phoneNumber: '+15550005678' }
                }
            ]
        }
    };

    try {
        await sendRingCentralWebhook(payload);
        activeConversations.set(agent.id, {
            ...(activeConversations.get(agent.id) || {}),
            callId: sessionId,
            callExtensionId: agent.ringcentral_extension_id,
            callAgentName: agent.name
        });

        utils.showSuccess(`Started call for ${agent.name}`);
        setTimeout(() => loadAgents(), 5000);
    } catch (error) {
        console.error('Failed to start call:', error);
        utils.showError(`Failed to start call: ${error.message}`);
    }
}

/**
 * End call for agent
 */
async function endCall(agent) {
    const conversation = activeConversations.get(agent.id);
    if (!conversation || !conversation.callId) {
        utils.showError('No active call for this agent');
        return;
    }

    const payload = {
        uuid: `webhook_${Date.now()}`,
        event: `/restapi/v1.0/account/~/extension/${agent.ringcentral_extension_id}/telephony/sessions`,
        timestamp: new Date().toISOString(),
        body: {
            sessionId: conversation.callId,
            extensionId: agent.ringcentral_extension_id,
            parties: [
                {
                    extensionId: agent.ringcentral_extension_id,
                    status: { code: 'Disconnected' }
                }
            ]
        }
    };

    try {
        await sendRingCentralWebhook(payload);

        const updated = activeConversations.get(agent.id);
        delete updated.callId;
        delete updated.callExtensionId;
        delete updated.callAgentName;
        if (Object.keys(updated).length === 0) {
            activeConversations.delete(agent.id);
        } else {
            activeConversations.set(agent.id, updated);
        }

        utils.showSuccess(`Ended call for ${agent.name}`);
        setTimeout(() => loadAgents(), 5000);
    } catch (error) {
        console.error('Failed to end call:', error);
        utils.showError(`Failed to end call: ${error.message}`);
    }
}

/**
 * Render the agents list
 * @param {Array} agents - Array of agent objects
 */
function renderAgents(agents) {
    const agentsList = document.getElementById('agents-list');

    if (!agents || agents.length === 0) {
        agentsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">👥</div>
                <div class="empty-state-text">No agents found</div>
            </div>
        `;
        return;
    }

    agentsList.innerHTML = agents.map(agent => {
        const currentState = agent.current_state;

        // Check if agent has active conversations (local state)
        const hasActiveChat = activeConversations.get(agent.id)?.chatId;
        const hasActiveCall = activeConversations.get(agent.id)?.callId;

        // Determine unified status based on LOCAL STATE first, then API data
        let statusText = 'Unknown';
        let statusClass = 'offline';
        let statusIcon = '❓';
        let stateChanged = 'N/A';

        // Priority: Check local active conversations first
        if (hasActiveChat && hasActiveCall) {
            // Both active - show chat (or we could show "Multi-tasking")
            statusText = 'Chatting';
            statusClass = 'busy';
            statusIcon = '💬';
            stateChanged = 'just now';
        } else if (hasActiveChat) {
            // Chat active
            statusText = 'Chatting';
            statusClass = 'busy';
            statusIcon = '💬';
            stateChanged = 'just now';
        } else if (hasActiveCall) {
            // Call active
            statusText = 'On Call';
            statusClass = 'busy';
            statusIcon = '📞';
            stateChanged = 'just now';
        } else if (currentState) {
            // No local active conversations - use API state
            const reason = currentState.reason || 'unknown';
            stateChanged = utils.getRelativeTime(currentState.state_changed_at);

            // Map reason to descriptive status
            if (reason === 'chatting') {
                statusText = 'Chatting';
                statusClass = 'busy';
                statusIcon = '💬';
            } else if (reason === 'on_call') {
                statusText = 'On Call';
                statusClass = 'busy';
                statusIcon = '📞';
            } else if (reason === 'available') {
                statusText = 'Available';
                statusClass = 'available';
                statusIcon = '✅';
            } else if (reason === 'on_livechat') {
                // Legacy reason
                statusText = 'Chatting';
                statusClass = 'busy';
                statusIcon = '💬';
            } else {
                statusText = 'Offline';
                statusClass = 'offline';
                statusIcon = '🔴';
            }
        } else {
            // No state at all - default to available
            statusText = 'Available';
            statusClass = 'available';
            statusIcon = '✅';
            stateChanged = 'N/A';
        }

        return `
            <div class="agent-card">
                <div class="agent-header">
                    <div class="agent-name">${agent.name || 'Unnamed Agent'}</div>
                    <div class="agent-email">${agent.email || 'No email'}</div>
                    <div class="agent-ids">
                        LC: ${agent.livechat_agent_id} | RC: ${agent.ringcentral_extension_id}
                    </div>
                </div>
                <div class="agent-status">
                    <div class="status-row status-main">
                        <span class="status-icon">${statusIcon}</span>
                        <span class="status-badge ${statusClass} status-large">${statusText}</span>
                    </div>
                    <div class="status-details">
                        <span class="status-detail-item">
                            LC: ${currentState ? (currentState.livechat_status === 'accepting_chats' ? '✓' : '✗') : '?'}
                        </span>
                        <span class="status-detail-item">
                            RC: ${currentState ? (currentState.ringcentral_presence === 'Available' ? '✓' : '✗') : '?'}
                        </span>
                    </div>
                </div>
                <div class="agent-meta">
                    <div>Last updated: <strong>${stateChanged}</strong></div>
                </div>
                <div class="agent-controls">
                    <div class="control-section">
                        <strong>💬 LiveChat:</strong>
                        <div class="button-group-inline">
                            ${!hasActiveChat ?
                                `<button class="btn-control btn-start-chat" data-agent-id="${agent.id}">Start Chat</button>` :
                                `<button class="btn-control btn-end-chat" data-agent-id="${agent.id}">End Chat</button>`
                            }
                        </div>
                    </div>
                    <div class="control-section">
                        <strong>📞 RingCentral:</strong>
                        <div class="button-group-inline">
                            ${!hasActiveCall ?
                                `<button class="btn-control btn-start-call" data-agent-id="${agent.id}">Start Call</button>` :
                                `<button class="btn-control btn-end-call" data-agent-id="${agent.id}">End Call</button>`
                            }
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    // Attach event listeners to buttons
    attachButtonListeners(agents);
}

/**
 * Attach event listeners to demo control buttons
 */
function attachButtonListeners(agents) {
    // Start Chat buttons
    document.querySelectorAll('.btn-start-chat').forEach(button => {
        button.addEventListener('click', () => {
            const agentId = parseInt(button.dataset.agentId);
            const agent = agents.find(a => a.id === agentId);
            if (agent) startChat(agent);
        });
    });

    // End Chat buttons
    document.querySelectorAll('.btn-end-chat').forEach(button => {
        button.addEventListener('click', () => {
            const agentId = parseInt(button.dataset.agentId);
            const agent = agents.find(a => a.id === agentId);
            if (agent) endChat(agent);
        });
    });

    // Start Call buttons
    document.querySelectorAll('.btn-start-call').forEach(button => {
        button.addEventListener('click', () => {
            const agentId = parseInt(button.dataset.agentId);
            const agent = agents.find(a => a.id === agentId);
            if (agent) startCall(agent);
        });
    });

    // End Call buttons
    document.querySelectorAll('.btn-end-call').forEach(button => {
        button.addEventListener('click', () => {
            const agentId = parseInt(button.dataset.agentId);
            const agent = agents.find(a => a.id === agentId);
            if (agent) endCall(agent);
        });
    });
}

/**
 * Load and display agents
 */
export async function loadAgents() {
    try {
        utils.hideError();
        utils.showLoading();

        const data = await api.getAgents();
        renderAgents(data.agents);

        utils.updateLastUpdateTime();
    } catch (error) {
        console.error('Failed to load agents:', error);
        utils.showError('Failed to load agents. Please try again.');
    } finally {
        utils.hideLoading();
    }
}

/**
 * Initialize agents view
 */
export function initAgentsView() {
    // Set up refresh button
    const refreshButton = document.getElementById('refresh-agents');
    if (refreshButton) {
        refreshButton.addEventListener('click', loadAgents);
    }

    // Load agents on init
    loadAgents();
}
