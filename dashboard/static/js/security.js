/* 
# This file is part of NeuraSelf-UwU.
# Copyright (c) 2025-Present Routo
#
# NeuraSelf-UwU is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with NeuraSelf-UwU. If not, see <https://www.gnu.org/licenses/>.
*/

const CAPTCHA_SERVICES = {
    browseruse: {
        label: 'BrowserUse',
        keyField: 'browseruse_api_key',
        balanceUnit: 'hrs',
        color: '#10b981',
        hint: 'Cloud browser with built-in captcha solving. $15 free credit (~750 hours).'
    },
};

let pendingCaptchas = {};
let pendingInterval = null;
let _manualSolvePopup = null;

async function testSecurity(btn) {
    const q = currentAccountId ? `?id=${currentAccountId}` : '';
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> TESTING...';
    btn.disabled = true;
    try {
        const res = await fetch(`/api/security/test${q}`, { method: 'POST' });
        const d = await res.json();
        if (d.status === 'success') {
            btn.style.borderColor = 'var(--success)';
            btn.innerHTML = '<i class="fa-solid fa-check"></i> SIGNALS SENT';
        } else {
            alert("Test failed: " + d.message);
            btn.innerHTML = original;
        }
    } catch (e) {
        alert("Request failed");
        btn.innerHTML = original;
    } finally {
        setTimeout(() => {
            btn.innerHTML = original;
            btn.disabled = false;
            btn.style.border = '';
        }, 3000);
    }
}

async function fetchSecuritySummary() {
    if (!document.getElementById('security').classList.contains('active-view')) return;
    const container = document.getElementById('security-accounts-grid');
    if (!container) return;
    let html = '';
    for (const acc of accountsList) {
        try {
            const res = await fetch(`/api/stats?id=${acc.id}`);
            const d = await res.json();
            if (!d || !d.security) continue;
            const isActive = acc.id === currentAccountId;
            const statusColor = d.status === "PAUSED" ? "var(--danger)" : "var(--success)";
            html += `
                <div class="sec-account-card ${d.status === "PAUSED" ? 'alert-active' : ''} ${isActive ? 'selected' : ''}">
                    <div class="sec-acc-header">
                        <div class="sec-acc-info">
                            ${acc.avatar ? `<img src="${acc.avatar}" class="account-avatar-lg" alt="">` : '<span class="icon-svg account-avatar-lg account-avatar-fallback" style="--icon: url(\'/static/assets/neura_icons/discord.svg\');"></span>'}
                            <div class="sec-acc-text">
                                <div class="sec-acc-name">${acc.username}</div>
                                <div class="sec-acc-id">User ID · ${acc.id}</div>
                                <div class="sec-acc-status" style="color:${statusColor}">${d.status}</div>
                            </div>
                        </div>
                    </div>
                    <div class="sec-acc-stats">
                        <div class="sec-mini-stat">
                            <span class="icon-svg" style="--icon: url('/static/assets/neura_icons/check-to-slot.svg'); background-color: var(--success);"></span>
                            <div class="val">${d.security.captchas}</div>
                            <div class="lbl">Solved</div>
                        </div>
                        <div class="sec-mini-stat">
                            <span class="icon-svg" style="--icon: url('/static/assets/neura_icons/user-slash.svg'); background-color: var(--danger);"></span>
                            <div class="val">${d.security.bans}</div>
                            <div class="lbl">Bans</div>
                        </div>
                        <div class="sec-mini-stat">
                            <span class="icon-svg" style="--icon: url('/static/assets/neura_icons/warning.svg'); background-color: var(--warning);"></span>
                            <div class="val">${d.security.warnings}</div>
                            <div class="lbl">Warns</div>
                        </div>
                    </div>
                </div>
            `;
        } catch (e) {}
    }
    container.innerHTML = html || '<div class="no-data">Initializing system details...</div>';
}

function renderCaptchaSolverWidget(cfg, basePath, parentEnabled) {
    const enabled    = cfg.enabled !== false;
    const service    = (cfg.service || 'browseruse').toLowerCase();
    const svcInfo    = CAPTCHA_SERVICES[service] || CAPTCHA_SERVICES.browseruse;
    const apiKey     = cfg[svcInfo.keyField] || '';
    const dis        = parentEnabled ? '' : ' disabled';
    const serviceOptions = Object.entries(CAPTCHA_SERVICES).map(([id, s]) => `
        <option value="${id}" ${id === service ? 'selected' : ''}>${s.label}</option>
    `).join('');
    return `
        <div class="cfg-row" data-path="${basePath}.enabled">
            <div class="cfg-row-label"><span class="cfg-label-text">Enable Auto-Solver</span></div>
            <div class="cfg-row-control">${renderNeuraToggle(basePath + '.enabled', enabled, parentEnabled, true)}</div>
        </div>
        <div class="cfg-row csw-service-row" data-path="${basePath}.service">
            <div class="cfg-row-label">
                <span class="cfg-label-text">Service</span>
                <span class="csw-service-hint">${svcInfo.hint}</span>
            </div>
            <div class="cfg-row-control">
                <div class="csw-dropdown-wrap">
                    <div class="csw-svc-dot" style="background:${svcInfo.color}"></div>
                    <select id="csw-service-select" class="csw-select" ${!enabled || !parentEnabled ? 'disabled' : ''}
                        onchange="updateCaptchaService(this.value)">
                        ${serviceOptions}
                    </select>
                </div>
            </div>
        </div>
        <div class="cfg-row csw-key-row" data-path="${basePath}.${svcInfo.keyField}" id="csw-key-row">
            <div class="cfg-row-label">
                <span class="cfg-label-text">${svcInfo.label} API Key</span>
            </div>
            <div class="cfg-row-control">
                <div class="cfg-input-wrap">
                    <input type="password" id="csw-api-key-input" class="cfg-input" value="${apiKey}"${dis}
                        placeholder="Paste your ${svcInfo.label} API key here…"
                        onchange="updateDeepVal('${basePath}.${svcInfo.keyField}', this.value)">
                </div>
            </div>
        </div>
        <div class="cfg-row csw-balance-row">
            <div class="cfg-row-label"><span class="cfg-label-text">Live Balance</span></div>
            <div class="cfg-row-control">
                <div class="csw-balance-wrap">
                    <span id="csw-balance-badge" class="csw-balance-badge" onclick="fetchCaptchaBalance()">
                        <span class="csw-balance-dot"></span>
                        <span id="csw-balance-text">Click to check…</span>
                    </span>
                    <button class="cfg-stepper-btn csw-refresh-btn" onclick="fetchCaptchaBalance()" title="Refresh balance">
                        <span class="icon-svg" style="--icon: url('/static/assets/neura_icons/sync.svg');"></span>
                    </button>
                </div>
            </div>
        </div>
    `;
}

window.updateCaptchaService = function(newService) {
    const basePath = 'security.captcha_solver';
    setDeep(currentConfig, `${basePath}.service`.split('.'), newService);
    checkDirty();
    renderSettings(currentConfig);
};

window.fetchCaptchaBalance = async function() {
    const badge   = document.getElementById('csw-balance-badge');
    const balText = document.getElementById('csw-balance-text');
    if (!badge || !balText) return;
    balText.textContent = 'Checking…';
    badge.className = 'csw-balance-badge loading';
    try {
        const q = currentAccountId ? `?id=${currentAccountId}` : '';
        const selectedService = getDeep(currentConfig, 'security.captcha_solver.service'.split('.')) || 'browseruse';
        const svcInfo = CAPTCHA_SERVICES[selectedService] || CAPTCHA_SERVICES.browseruse;
        const currentKey = getDeep(currentConfig, `security.captcha_solver.${svcInfo.keyField}`.split('.')) || '';
        const res = await fetch(`/api/captcha/balance${q}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ service: selectedService, api_key: currentKey })
        });
        const d = await res.json();
        if (d.error || d.balance === null || d.balance === undefined) {
            balText.textContent = d.message || d.error || 'Error – check API key';
            badge.className = 'csw-balance-badge error';
        } else {
            let balance = d.balance;
            let unit = svcInfo.balanceUnit;
            let display;
            if (typeof balance === 'number') {
                if (unit === '$') display = `$${balance.toFixed(2)}`;
                else display = `${Math.round(balance).toLocaleString()} ${unit}`;
            } else {
                display = String(balance);
            }
            balText.textContent = display;
            badge.className = 'csw-balance-badge ok';
        }
    } catch (e) {
        balText.textContent = 'Request failed';
        badge.className = 'csw-balance-badge error';
    }
};

async function updatePendingCaptchas() {
    try {
        const res = await fetch('/api/captcha/pending');
        const data = await res.json();
        const pending = data.pending || [];
        const newPending = {};
        pending.forEach(p => {
            newPending[p.account_id] = {
                accountId: p.account_id,
                accountName: p.account_name || p.account_id,
                createdAt: p.created_at
            };
        });
        Object.keys(pendingCaptchas).forEach(id => {
            if (!newPending[id]) delete pendingCaptchas[id];
        });
        Object.keys(newPending).forEach(id => {
            if (!pendingCaptchas[id]) pendingCaptchas[id] = newPending[id];
        });
        updateNotificationUI();
    } catch (e) {
        console.error('Failed to fetch pending captchas:', e);
    }
}

function updateNotificationUI() {
    const count = Object.keys(pendingCaptchas).length;
    const bell = document.getElementById('notification-bell');
    const badge = document.getElementById('notification-badge');
    if (bell) {
        if (count > 0) {
            bell.classList.add('has-alert');
            badge.textContent = count;
            badge.style.display = 'block';
        } else {
            bell.classList.remove('has-alert');
            badge.style.display = 'none';
        }
    }
    renderPendingDropdown();
    renderSecurityCards();
}

function renderPendingDropdown() {
    const dropdown = document.getElementById('notification-dropdown');
    if (!dropdown) return;
    const count = Object.keys(pendingCaptchas).length;
    if (count === 0) {
        dropdown.innerHTML = '<div class="no-data">No pending captchas</div>';
        return;
    }
    let html = '';
    const now = Date.now() / 1000;
    Object.values(pendingCaptchas).forEach(p => {
        const elapsed = now - p.createdAt;
        const remaining = Math.max(0, 600 - elapsed);
        const urgencyClass = getUrgencyClass(remaining);
        const timeStr = formatTime(remaining);
        html += `
            <div class="pending-item ${urgencyClass}">
                <span class="pending-name">${p.accountName}</span>
                <span class="pending-timer">${timeStr}</span>
                <button class="btn-proxy-sm solve-btn" onclick="triggerManualSolve('${p.accountId}')">Solve</button>
            </div>
        `;
    });
    dropdown.innerHTML = html;
}

function renderSecurityCards() {
    const container = document.getElementById('captcha-cards-container');
    if (!container) return;
    const count = Object.keys(pendingCaptchas).length;
    if (count === 0) {
        container.innerHTML = '<div class="no-data">No pending captchas</div>';
        return;
    }
    let html = '';
    const now = Date.now() / 1000;
    Object.values(pendingCaptchas).forEach(p => {
        const elapsed = now - p.createdAt;
        const remaining = Math.max(0, 600 - elapsed);
        const urgencyClass = getUrgencyClass(remaining);
        const timeStr = formatTime(remaining);
        html += `
            <div class="captcha-card ${urgencyClass}">
                <div class="captcha-card-header">
                    <span class="captcha-account">${p.accountName}</span>
                    <span class="captcha-timer">${timeStr}</span>
                </div>
                <div class="captcha-card-body">
                    <button class="btn-control gold" onclick="triggerManualSolve('${p.accountId}')">Solve</button>
                    <button class="btn-control" onclick="dismissCaptchaCard('${p.accountId}')">Dismiss</button>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function dismissCaptchaCard(accountId) {
    if (pendingCaptchas[accountId]) {
        delete pendingCaptchas[accountId];
        updateNotificationUI();
    }
}

function getUrgencyClass(seconds) {
    if (seconds > 300) return 'urgency-green';
    if (seconds > 120) return 'urgency-yellow';
    if (seconds > 60) return 'urgency-orange';
    if (seconds > 30) return 'urgency-red';
    return 'urgency-critical';
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
}

window.triggerManualSolve = async function(accountId) {
    try {
        const res = await fetch('/api/captcha/oauth_url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ account_id: accountId })
        });
        const data = await res.json();
        if (!data.success || !data.url) {
            showToast('Failed to get captcha URL', 'error');
            return;
        }
        const popup = window.open(data.url, '_blank', 'width=420,height=600,resizable=yes,scrollbars=yes');
        if (!popup) {
            window.open(data.url, '_blank');
        } else {
            _manualSolvePopup = popup;
        }
        showToast('Captcha page opened in new window', 'info');
    } catch (e) {
        showToast('Error opening captcha', 'error');
    }
};

window.pollForCaptchas = async function() {
    await updatePendingCaptchas();
};

function startPendingTimer() {
    if (pendingInterval) clearInterval(pendingInterval);
    pendingInterval = setInterval(() => {
        if (Object.keys(pendingCaptchas).length > 0) {
            renderPendingDropdown();
            renderSecurityCards();
        }
    }, 1000);
}

window.toggleNotificationDropdown = function() {
    const dropdown = document.getElementById('notification-dropdown');
    if (!dropdown) return;
    if (dropdown.style.display === 'block') {
        dropdown.style.display = 'none';
    } else {
        dropdown.style.display = 'block';
        document.addEventListener('click', function closeDropdown(e) {
            const bell = document.getElementById('notification-bell');
            if (bell && !bell.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
                document.removeEventListener('click', closeDropdown);
            }
        });
    }
};

window.cancelManualSolve = function() {
    if (_manualSolvePopup) {
        try { _manualSolvePopup.close(); } catch (e) {}
        _manualSolvePopup = null;
    }
};

window.cancelEmbeddedCaptcha = window.cancelManualSolve;

startPendingTimer();            alert("Test failed: " + d.message);
            btn.innerHTML = original;
        }
    } catch (e) {
        alert("Request failed");
        btn.innerHTML = original;
    } finally {
        setTimeout(() => {
            btn.innerHTML = original;
            btn.disabled = false;
            btn.style.border = '';
        }, 3000);
    }
}

async function fetchSecuritySummary() {
    if (!document.getElementById('security').classList.contains('active-view')) return;
    const container = document.getElementById('security-accounts-grid');
    if (!container) return;
    let html = '';
    for (const acc of accountsList) {
        try {
            const res = await fetch(`/api/stats?id=${acc.id}`);
            const d = await res.json();
            if (!d || !d.security) continue;
            const isActive = acc.id === currentAccountId;
            const statusColor = d.status === "PAUSED" ? "var(--danger)" : "var(--success)";
            html += `
                <div class="sec-account-card ${d.status === "PAUSED" ? 'alert-active' : ''} ${isActive ? 'selected' : ''}">
                    <div class="sec-acc-header">
                        <div class="sec-acc-info">
                            ${acc.avatar ? `<img src="${acc.avatar}" class="account-avatar-lg" alt="">` : '<span class="icon-svg account-avatar-lg account-avatar-fallback" style="--icon: url(\'/static/assets/neura_icons/discord.svg\');"></span>'}
                            <div class="sec-acc-text">
                                <div class="sec-acc-name">${acc.username}</div>
                                <div class="sec-acc-id">User ID · ${acc.id}</div>
                                <div class="sec-acc-status" style="color:${statusColor}">${d.status}</div>
                            </div>
                        </div>
                    </div>
                    <div class="sec-acc-stats">
                        <div class="sec-mini-stat">
                            <span class="icon-svg" style="--icon: url('/static/assets/neura_icons/check-to-slot.svg'); background-color: var(--success);"></span>
                            <div class="val">${d.security.captchas}</div>
                            <div class="lbl">Solved</div>
                        </div>
                        <div class="sec-mini-stat">
                            <span class="icon-svg" style="--icon: url('/static/assets/neura_icons/user-slash.svg'); background-color: var(--danger);"></span>
                            <div class="val">${d.security.bans}</div>
                            <div class="lbl">Bans</div>
                        </div>
                        <div class="sec-mini-stat">
                            <span class="icon-svg" style="--icon: url('/static/assets/neura_icons/warning.svg'); background-color: var(--warning);"></span>
                            <div class="val">${d.security.warnings}</div>
                            <div class="lbl">Warns</div>
                        </div>
                    </div>
                </div>
            `;
        } catch (e) {}
    }
    container.innerHTML = html || '<div class="no-data">Initializing system details...</div>';
}

function renderCaptchaSolverWidget(cfg, basePath, parentEnabled) {
    const enabled    = cfg.enabled !== false;
    const service    = (cfg.service || 'yescaptcha').toLowerCase();
    const svcInfo    = CAPTCHA_SERVICES[service] || CAPTCHA_SERVICES.yescaptcha;
    const apiKey     = cfg[svcInfo.keyField] || '';
    const dis        = parentEnabled ? '' : ' disabled';
    const serviceOptions = Object.entries(CAPTCHA_SERVICES).map(([id, s]) => `
        <option value="${id}" ${id === service ? 'selected' : ''}>${s.label}</option>
    `).join('');
    return `
        <div class="cfg-row" data-path="${basePath}.enabled">
            <div class="cfg-row-label"><span class="cfg-label-text">Enable Auto-Solver</span></div>
            <div class="cfg-row-control">${renderNeuraToggle(basePath + '.enabled', enabled, parentEnabled, true)}</div>
        </div>
        <div class="cfg-row csw-service-row" data-path="${basePath}.service">
            <div class="cfg-row-label">
                <span class="cfg-label-text">Service</span>
                <span class="csw-service-hint">${svcInfo.hint}</span>
            </div>
            <div class="cfg-row-control">
                <div class="csw-dropdown-wrap">
                    <div class="csw-svc-dot" style="background:${svcInfo.color}"></div>
                    <select id="csw-service-select" class="csw-select" ${!enabled || !parentEnabled ? 'disabled' : ''}
                        onchange="updateCaptchaService(this.value)">
                        ${serviceOptions}
                    </select>
                </div>
            </div>
        </div>
        <div class="cfg-row csw-key-row" data-path="${basePath}.${svcInfo.keyField}" id="csw-key-row">
            <div class="cfg-row-label">
                <span class="cfg-label-text">${svcInfo.label} API Key</span>
            </div>
            <div class="cfg-row-control">
                <div class="cfg-input-wrap">
                    <input type="password" id="csw-api-key-input" class="cfg-input" value="${apiKey}"${dis}
                        placeholder="Paste your ${svcInfo.label} API key here…"
                        onchange="updateDeepVal('${basePath}.${svcInfo.keyField}', this.value)">
                </div>
            </div>
        </div>
        <div class="cfg-row csw-balance-row">
            <div class="cfg-row-label"><span class="cfg-label-text">Live Balance</span></div>
            <div class="cfg-row-control">
                <div class="csw-balance-wrap">
                    <span id="csw-balance-badge" class="csw-balance-badge" onclick="fetchCaptchaBalance()">
                        <span class="csw-balance-dot"></span>
                        <span id="csw-balance-text">Click to check…</span>
                    </span>
                    <button class="cfg-stepper-btn csw-refresh-btn" onclick="fetchCaptchaBalance()" title="Refresh balance">
                        <span class="icon-svg" style="--icon: url('/static/assets/neura_icons/sync.svg');"></span>
                    </button>
                </div>
            </div>
        </div>
    `;
}

window.updateCaptchaService = function(newService) {
    const basePath = 'security.captcha_solver';
    setDeep(currentConfig, `${basePath}.service`.split('.'), newService);
    checkDirty();
    renderSettings(currentConfig);
};

window.fetchCaptchaBalance = async function() {
    const badge   = document.getElementById('csw-balance-badge');
    const balText = document.getElementById('csw-balance-text');
    if (!badge || !balText) return;
    balText.textContent = 'Checking…';
    badge.className = 'csw-balance-badge loading';
    try {
        const q = currentAccountId ? `?id=${currentAccountId}` : '';
        const selectedService = getDeep(currentConfig, 'security.captcha_solver.service'.split('.')) || 'yescaptcha';
        const svcInfo = CAPTCHA_SERVICES[selectedService] || CAPTCHA_SERVICES.yescaptcha;
        const currentKey = getDeep(currentConfig, `security.captcha_solver.${svcInfo.keyField}`.split('.')) || '';
        const res = await fetch(`/api/captcha/balance${q}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ service: selectedService, api_key: currentKey })
        });
        const d = await res.json();
        if (d.error || d.balance === null || d.balance === undefined) {
            balText.textContent = d.message || d.error || 'Error – check API key';
            badge.className = 'csw-balance-badge error';
        } else {
            let balance = d.balance;
            let unit = svcInfo.balanceUnit;
            let display;
            if (typeof balance === 'number') {
                if (unit === '$') display = `$${balance.toFixed(2)}`;
                else display = `${Math.round(balance).toLocaleString()} ${unit}`;
            } else {
                display = String(balance);
            }
            balText.textContent = display;
            badge.className = 'csw-balance-badge ok';
        }
    } catch (e) {
        balText.textContent = 'Request failed';
        badge.className = 'csw-balance-badge error';
    }
};

async function updatePendingCaptchas() {
    try {
        const res = await fetch('/api/captcha/pending');
        const data = await res.json();
        const pending = data.pending || [];
        const newPending = {};
        pending.forEach(p => {
            newPending[p.account_id] = {
                accountId: p.account_id,
                accountName: p.account_name || p.account_id,
                createdAt: p.created_at
            };
        });
        Object.keys(pendingCaptchas).forEach(id => {
            if (!newPending[id]) delete pendingCaptchas[id];
        });
        Object.keys(newPending).forEach(id => {
            if (!pendingCaptchas[id]) pendingCaptchas[id] = newPending[id];
        });
        updateNotificationUI();
    } catch (e) {
        console.error('Failed to fetch pending captchas:', e);
    }
}

function updateNotificationUI() {
    const count = Object.keys(pendingCaptchas).length;
    const bell = document.getElementById('notification-bell');
    const badge = document.getElementById('notification-badge');
    if (bell) {
        if (count > 0) {
            bell.classList.add('has-alert');
            badge.textContent = count;
            badge.style.display = 'block';
        } else {
            bell.classList.remove('has-alert');
            badge.style.display = 'none';
        }
    }
    renderPendingDropdown();
    renderSecurityCards();
}

function renderPendingDropdown() {
    const dropdown = document.getElementById('notification-dropdown');
    if (!dropdown) return;
    const count = Object.keys(pendingCaptchas).length;
    if (count === 0) {
        dropdown.innerHTML = '<div class="no-data">No pending captchas</div>';
        return;
    }
    let html = '';
    const now = Date.now() / 1000;
    Object.values(pendingCaptchas).forEach(p => {
        const elapsed = now - p.createdAt;
        const remaining = Math.max(0, 600 - elapsed);
        const urgencyClass = getUrgencyClass(remaining);
        const timeStr = formatTime(remaining);
        html += `
            <div class="pending-item ${urgencyClass}">
                <span class="pending-name">${p.accountName}</span>
                <span class="pending-timer">${timeStr}</span>
                <button class="btn-proxy-sm solve-btn" onclick="triggerManualSolve('${p.accountId}')">Solve</button>
            </div>
        `;
    });
    dropdown.innerHTML = html;
}

function renderSecurityCards() {
    const container = document.getElementById('captcha-cards-container');
    if (!container) return;
    const count = Object.keys(pendingCaptchas).length;
    if (count === 0) {
        container.innerHTML = '<div class="no-data">No pending captchas</div>';
        return;
    }
    let html = '';
    const now = Date.now() / 1000;
    Object.values(pendingCaptchas).forEach(p => {
        const elapsed = now - p.createdAt;
        const remaining = Math.max(0, 600 - elapsed);
        const urgencyClass = getUrgencyClass(remaining);
        const timeStr = formatTime(remaining);
        html += `
            <div class="captcha-card ${urgencyClass}">
                <div class="captcha-card-header">
                    <span class="captcha-account">${p.accountName}</span>
                    <span class="captcha-timer">${timeStr}</span>
                </div>
                <div class="captcha-card-body">
                    <button class="btn-control gold" onclick="triggerManualSolve('${p.accountId}')">Solve</button>
                    <button class="btn-control" onclick="dismissCaptchaCard('${p.accountId}')">Dismiss</button>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function dismissCaptchaCard(accountId) {
    if (pendingCaptchas[accountId]) {
        delete pendingCaptchas[accountId];
        updateNotificationUI();
    }
}

function getUrgencyClass(seconds) {
    if (seconds > 300) return 'urgency-green';
    if (seconds > 120) return 'urgency-yellow';
    if (seconds > 60) return 'urgency-orange';
    if (seconds > 30) return 'urgency-red';
    return 'urgency-critical';
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
}

window.triggerManualSolve = async function(accountId) {
    try {
        const res = await fetch('/api/captcha/oauth_url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ account_id: accountId })
        });
        const data = await res.json();
        if (!data.success || !data.url) {
            showToast('Failed to get captcha URL', 'error');
            return;
        }
        const popup = window.open(data.url, '_blank', 'width=420,height=600,resizable=yes,scrollbars=yes');
        if (!popup) {
            window.open(data.url, '_blank');
        } else {
            _manualSolvePopup = popup;
        }
        showToast('Captcha page opened in new window', 'info');
    } catch (e) {
        showToast('Error opening captcha', 'error');
    }
};

window.pollForCaptchas = async function() {
    await updatePendingCaptchas();
};

function startPendingTimer() {
    if (pendingInterval) clearInterval(pendingInterval);
    pendingInterval = setInterval(() => {
        if (Object.keys(pendingCaptchas).length > 0) {
            renderPendingDropdown();
            renderSecurityCards();
        }
    }, 1000);
}

window.toggleNotificationDropdown = function() {
    const dropdown = document.getElementById('notification-dropdown');
    if (!dropdown) return;
    if (dropdown.style.display === 'block') {
        dropdown.style.display = 'none';
    } else {
        dropdown.style.display = 'block';
        document.addEventListener('click', function closeDropdown(e) {
            const bell = document.getElementById('notification-bell');
            if (bell && !bell.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
                document.removeEventListener('click', closeDropdown);
            }
        });
    }
};

window.cancelManualSolve = function() {
    if (_manualSolvePopup) {
        try { _manualSolvePopup.close(); } catch (e) {}
        _manualSolvePopup = null;
    }
};

window.cancelEmbeddedCaptcha = window.cancelManualSolve;

startPendingTimer();
