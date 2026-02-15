/**
 * Demo controls module
 */

import * as utils from './utils.js';
import { loadAgents } from './agents.js';

// Track active chats and calls
let activeChats = [];
let activeCalls = [];

/**
 * Show update notification
 */
function showUpdateNotification(message) {
    // Create or get notification element
    let notification = document.getElementById('update-notification');

    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'update-notification';
        notification.className = 'update-notification';
        document.body.appendChild(notification);
    }

    notification.textContent = message;
    notification.classList.add('show');

    // Hide after 2 seconds
    setTimeout(() => {
        notification.classList.remove('show');
    }, 2000);
}

/**
 * Add log entry to activity log
 */
function addLogEntry(message, type = 'info') {
    const logContainer = document.getElementById('demo-log');
    const emptyMessage = logContainer.querySelector('.log-empty');

    if (emptyMessage) {
        emptyMessage.remove();
    }

    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;

    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-time">[${timestamp}]</span> ${message}`;

    logContainer.insertBefore(entry, logContainer.firstChild);

    // Keep only last 20 entries
    const entries = logContainer.querySelectorAll('.log-entry');
    if (entries.length > 20) {
        entries[entries.length - 1].remove();
    }
}

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
        headers: {
            'Content-Type': 'application/json',
        },
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
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
    }

    return await response.json();
}

/**
 * Start a LiveChat chat
 */
async function startLiveChat() {
    const agentSelect = document.getElementById('livechat-agent-select');
    const agentId = agentSelect.value;
    const agentName = agentSelect.options[agentSelect.selectedIndex].text.split(' (')[0];

    const chatId = `demo_chat_${Date.now()}`;

    const payload = {
        webhook_id: `webhook_${Date.now()}`,
        action: 'incoming_chat',
        payload: {
            chat: {
                id: chatId,
                users: [
                    {
                        id: agentId,
                        type: 'agent',
                        email: 'agent@example.com',
                        name: agentName
                    },
                    {
                        id: 'customer_demo',
                        type: 'customer',
                        email: 'customer@demo.com',
                        name: 'Demo Customer'
                    }
                ],
                thread: {
                    active: true
                }
            }
        }
    };

    try {
        addLogEntry(`Starting chat for ${agentName}...`, 'info');
        await sendLiveChatWebhook('incoming_chat', payload);
        activeChats.push({ chatId, agentId, agentName });
        addLogEntry(`✓ Chat started for ${agentName} (ID: ${chatId})`, 'success');

        // Refresh agents view after Celery task processes (5 seconds for API timeouts)
        setTimeout(() => {
            loadAgents();
            showUpdateNotification('Agent status updated!');
        }, 5000);
    } catch (error) {
        console.error('Failed to start chat:', error);
        addLogEntry(`✗ Failed to start chat: ${error.message}`, 'error');
        utils.showError('Failed to start chat. Check console for details.');
    }
}

/**
 * End the last LiveChat chat
 */
async function endLiveChat() {
    if (activeChats.length === 0) {
        addLogEntry('No active chats to end', 'warning');
        utils.showError('No active chats to end');
        return;
    }

    const lastChat = activeChats.pop();

    const payload = {
        webhook_id: `webhook_${Date.now()}`,
        action: 'chat_deactivated',
        payload: {
            chat: {
                id: lastChat.chatId,
                users: [
                    {
                        id: lastChat.agentId,
                        type: 'agent',
                        name: lastChat.agentName
                    }
                ]
            }
        }
    };

    try {
        addLogEntry(`Ending chat for ${lastChat.agentName}...`, 'info');
        await sendLiveChatWebhook('chat_deactivated', payload);
        addLogEntry(`✓ Chat ended for ${lastChat.agentName}`, 'success');

        // Refresh agents view after Celery task processes (5 seconds for API timeouts)
        setTimeout(() => {
            loadAgents();
            showUpdateNotification('Agent status updated!');
        }, 5000);
    } catch (error) {
        console.error('Failed to end chat:', error);
        addLogEntry(`✗ Failed to end chat: ${error.message}`, 'error');
        utils.showError('Failed to end chat. Check console for details.');
        // Put it back if it failed
        activeChats.push(lastChat);
    }
}

/**
 * Start a RingCentral call
 */
async function startRingCentralCall() {
    const extensionSelect = document.getElementById('ringcentral-extension-select');
    const extensionId = extensionSelect.value;
    const agentName = extensionSelect.options[extensionSelect.selectedIndex].text.split(' (')[0];

    const sessionId = `demo_session_${Date.now()}`;

    const payload = {
        uuid: `webhook_${Date.now()}`,
        event: `/restapi/v1.0/account/~/extension/${extensionId}/telephony/sessions`,
        timestamp: new Date().toISOString(),
        body: {
            sessionId: sessionId,
            extensionId: extensionId,
            parties: [
                {
                    extensionId: extensionId,
                    status: {
                        code: 'Answered'
                    },
                    direction: 'Inbound',
                    from: {
                        phoneNumber: '+15550001234'
                    },
                    to: {
                        phoneNumber: '+15550005678'
                    }
                }
            ]
        }
    };

    try {
        addLogEntry(`Starting call for ${agentName}...`, 'info');
        await sendRingCentralWebhook(payload);
        activeCalls.push({ sessionId, extensionId, agentName });
        addLogEntry(`✓ Call started for ${agentName} (Session: ${sessionId})`, 'success');

        // Refresh agents view after Celery task processes (5 seconds for API timeouts)
        setTimeout(() => {
            loadAgents();
            showUpdateNotification('Agent status updated!');
        }, 5000);
    } catch (error) {
        console.error('Failed to start call:', error);
        addLogEntry(`✗ Failed to start call: ${error.message}`, 'error');
        utils.showError('Failed to start call. Check console for details.');
    }
}

/**
 * End the last RingCentral call
 */
async function endRingCentralCall() {
    if (activeCalls.length === 0) {
        addLogEntry('No active calls to end', 'warning');
        utils.showError('No active calls to end');
        return;
    }

    const lastCall = activeCalls.pop();

    const payload = {
        uuid: `webhook_${Date.now()}`,
        event: `/restapi/v1.0/account/~/extension/${lastCall.extensionId}/telephony/sessions`,
        timestamp: new Date().toISOString(),
        body: {
            sessionId: lastCall.sessionId,
            extensionId: lastCall.extensionId,
            parties: [
                {
                    extensionId: lastCall.extensionId,
                    status: {
                        code: 'Disconnected'
                    }
                }
            ]
        }
    };

    try {
        addLogEntry(`Ending call for ${lastCall.agentName}...`, 'info');
        await sendRingCentralWebhook(payload);
        addLogEntry(`✓ Call ended for ${lastCall.agentName}`, 'success');

        // Refresh agents view after Celery task processes (5 seconds for API timeouts)
        setTimeout(() => {
            loadAgents();
            showUpdateNotification('Agent status updated!');
        }, 5000);
    } catch (error) {
        console.error('Failed to end call:', error);
        addLogEntry(`✗ Failed to end call: ${error.message}`, 'error');
        utils.showError('Failed to end call. Check console for details.');
        // Put it back if it failed
        activeCalls.push(lastCall);
    }
}

/**
 * Run scenario: Single chat
 */
async function runScenarioSingleChat() {
    addLogEntry('🎬 Starting Single Chat scenario...', 'info');

    await startLiveChat();

    addLogEntry('⏰ Waiting 5 seconds...', 'info');
    await new Promise(resolve => setTimeout(resolve, 5000));

    await endLiveChat();

    addLogEntry('✓ Single Chat scenario complete!', 'success');
}

/**
 * Run scenario: Single call
 */
async function runScenarioSingleCall() {
    addLogEntry('🎬 Starting Single Call scenario...', 'info');

    await startRingCentralCall();

    addLogEntry('⏰ Waiting 5 seconds...', 'info');
    await new Promise(resolve => setTimeout(resolve, 5000));

    await endRingCentralCall();

    addLogEntry('✓ Single Call scenario complete!', 'success');
}

/**
 * Run scenario: Cross-platform
 */
async function runScenarioCrossPlatform() {
    addLogEntry('🎬 Starting Cross-Platform scenario...', 'info');

    // Agent 1 gets a chat
    document.getElementById('livechat-agent-select').value = 'lc_agent_002';
    await startLiveChat();

    await new Promise(resolve => setTimeout(resolve, 2000));

    // Agent 2 gets a call
    document.getElementById('ringcentral-extension-select').value = '103';
    await startRingCentralCall();

    await new Promise(resolve => setTimeout(resolve, 3000));

    // End chat
    await endLiveChat();

    await new Promise(resolve => setTimeout(resolve, 2000));

    // End call
    await endRingCentralCall();

    addLogEntry('✓ Cross-Platform scenario complete!', 'success');
}

/**
 * Initialize demo controls
 */
export function initDemoControls() {
    // LiveChat controls
    document.getElementById('btn-start-chat')?.addEventListener('click', startLiveChat);
    document.getElementById('btn-end-chat')?.addEventListener('click', endLiveChat);

    // RingCentral controls
    document.getElementById('btn-start-call')?.addEventListener('click', startRingCentralCall);
    document.getElementById('btn-end-call')?.addEventListener('click', endRingCentralCall);

    // Scenario buttons
    document.getElementById('btn-scenario-single-chat')?.addEventListener('click', runScenarioSingleChat);
    document.getElementById('btn-scenario-single-call')?.addEventListener('click', runScenarioSingleCall);
    document.getElementById('btn-scenario-both')?.addEventListener('click', runScenarioCrossPlatform);

    console.log('Demo controls initialized');
}
