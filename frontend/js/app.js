/**
 * Main application module
 */

import * as api from './api.js';
import * as utils from './utils.js';
import { initAgentsView, loadAgents } from './agents.js';
import { initConversationsView, loadConversations } from './conversations.js';

// Current active tab
let currentTab = 'agents';

// Auto-refresh interval (10 seconds)
const AUTO_REFRESH_INTERVAL = 10000;
let autoRefreshTimer = null;

/**
 * Render the stats display
 * @param {object} stats - Stats object
 */
function renderStats(stats) {
    const statsDisplay = document.getElementById('stats-display');

    if (!stats) {
        statsDisplay.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📊</div>
                <div class="empty-state-text">No statistics available</div>
            </div>
        `;
        return;
    }

    statsDisplay.innerHTML = `
        <div class="stat-card primary">
            <div class="stat-label">Total Agents</div>
            <div class="stat-value">${stats.total_agents}</div>
        </div>
        <div class="stat-card success">
            <div class="stat-label">Available Agents</div>
            <div class="stat-value">${stats.agents_available}</div>
        </div>
        <div class="stat-card warning">
            <div class="stat-label">Busy Agents</div>
            <div class="stat-value">${stats.agents_busy}</div>
        </div>
        <div class="stat-card danger">
            <div class="stat-label">Offline Agents</div>
            <div class="stat-value">${stats.agents_offline}</div>
        </div>
        <div class="stat-card primary">
            <div class="stat-label">Active Conversations</div>
            <div class="stat-value">${stats.active_conversations}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Conversations Today</div>
            <div class="stat-value">${stats.total_conversations_today}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total Conversations</div>
            <div class="stat-value">${stats.total_conversations_all_time}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Sync Operations Today</div>
            <div class="stat-value">${stats.sync_operations_today}</div>
        </div>
        <div class="stat-card ${stats.sync_success_rate >= 95 ? 'success' : 'warning'}">
            <div class="stat-label">Sync Success Rate</div>
            <div class="stat-value">${stats.sync_success_rate}%</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Last Sync</div>
            <div class="stat-value" style="font-size: 18px;">
                ${stats.last_sync_at ? utils.getRelativeTime(stats.last_sync_at) : 'Never'}
            </div>
        </div>
    `;
}

/**
 * Load and display stats
 */
async function loadStats() {
    try {
        utils.hideError();
        utils.showLoading();

        const stats = await api.getStats();
        renderStats(stats);

        utils.updateLastUpdateTime();
    } catch (error) {
        console.error('Failed to load stats:', error);
        utils.showError('Failed to load statistics. Please try again.');
    } finally {
        utils.hideLoading();
    }
}

/**
 * Switch to a different tab
 * @param {string} tabName - Name of the tab to switch to
 */
function switchTab(tabName) {
    // Update current tab
    currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        if (button.dataset.tab === tabName) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        if (content.id === `${tabName}-tab`) {
            content.classList.remove('hidden');
            content.classList.add('active');
        } else {
            content.classList.add('hidden');
            content.classList.remove('active');
        }
    });

    // Load data for the active tab
    refreshCurrentTab();
}

/**
 * Refresh the current tab's data
 */
function refreshCurrentTab() {
    switch (currentTab) {
        case 'agents':
            loadAgents();
            break;
        case 'conversations':
            loadConversations();
            break;
        case 'stats':
            loadStats();
            break;
    }
}

/**
 * Start auto-refresh timer
 */
function startAutoRefresh() {
    // Clear any existing timer
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
    }

    // Set up new timer
    autoRefreshTimer = setInterval(() => {
        refreshCurrentTab();
    }, AUTO_REFRESH_INTERVAL);
}

/**
 * Initialize the application
 */
function init() {
    console.log('Initializing LiveChat-RingCentral Sync Dashboard...');

    // Set up tab navigation
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            switchTab(button.dataset.tab);
        });
    });

    // Set up stats refresh button
    const statsRefreshButton = document.getElementById('refresh-stats');
    if (statsRefreshButton) {
        statsRefreshButton.addEventListener('click', loadStats);
    }

    // Initialize views
    initAgentsView();
    initConversationsView();

    // Start with agents tab
    switchTab('agents');

    // Start auto-refresh
    startAutoRefresh();

    console.log('Dashboard initialized successfully');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
