/* AI Session Hub — Frontend SPA Logic */

const API = '';
let currentView = 'dashboard';
let currentSessionPage = 1;
let currentSearchPage = 1;
let currentSearchQuery = '';

// --- Navigation ---

function navigate(view, data) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    document.getElementById(`view-${view}`).classList.remove('hidden');
    currentView = view;

    switch(view) {
        case 'dashboard': loadDashboard(); break;
        case 'browse': loadSessions(1); break;
        case 'session': loadSessionDetail(data); break;
        case 'search': break; // loaded by doSearch
    }
}

// --- API helpers ---

async function api(path) {
    const res = await fetch(`${API}${path}`);
    return res.json();
}

async function apiPost(path) {
    const res = await fetch(`${API}${path}`, { method: 'POST' });
    return res.json();
}

// --- Dashboard ---

async function loadDashboard() {
    const stats = await api('/api/stats');

    // Stats cards
    const grid = document.getElementById('stats-grid');
    grid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${stats.total_sessions.toLocaleString()}</div>
            <div class="stat-label">Total Sessions</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.total_messages.toLocaleString()}</div>
            <div class="stat-label">Total Messages</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.total_size_mb.toFixed(1)} MB</div>
            <div class="stat-label">Indexed Data</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.tools_with_data}</div>
            <div class="stat-label">Tools Connected</div>
        </div>
    `;

    // Tool breakdown bars
    if (stats.by_tool && stats.by_tool.length > 0) {
        const maxCount = stats.by_tool[0].count;
        let barsHtml = '<h2>Sessions by Tool</h2><div style="margin-bottom:24px">';
        for (const t of stats.by_tool) {
            const pct = (t.count / maxCount * 100).toFixed(1);
            barsHtml += `
                <div class="tool-bar">
                    <span class="tool-bar-label">${toolDisplayName(t.tool)}</span>
                    <div class="tool-bar-fill" style="width:${pct}%"></div>
                    <span class="tool-bar-count">${t.count}</span>
                </div>
            `;
        }
        barsHtml += '</div>';
        grid.insertAdjacentHTML('afterend', barsHtml);
    }

    // Recent sessions
    const container = document.getElementById('recent-sessions');
    if (stats.recent_sessions && stats.recent_sessions.length > 0) {
        container.innerHTML = stats.recent_sessions.map(s => sessionCard(s)).join('');
    } else {
        container.innerHTML = '<p style="color:var(--text-secondary)">No sessions yet. Run a sync to get started.</p>';
    }
}

// --- Browse Sessions ---

async function loadSessions(page) {
    currentSessionPage = page;
    const tool = document.getElementById('filter-tool').value;
    const dateFrom = document.getElementById('filter-from').value;
    const dateTo = document.getElementById('filter-to').value;
    const project = document.getElementById('filter-project').value;

    let qs = `page=${page}&per_page=30`;
    if (tool) qs += `&tool=${encodeURIComponent(tool)}`;
    if (dateFrom) qs += `&date_from=${dateFrom}`;
    if (dateTo) qs += `&date_to=${dateTo}`;
    if (project) qs += `&project=${encodeURIComponent(project)}`;

    const data = await api(`/api/sessions?${qs}`);

    const container = document.getElementById('browse-sessions');
    if (data.sessions.length > 0) {
        container.innerHTML = data.sessions.map(s => sessionCard(s)).join('');
    } else {
        container.innerHTML = '<p style="color:var(--text-secondary)">No sessions found.</p>';
    }

    renderPagination('browse-pagination', data, (p) => loadSessions(p));
}

// --- Session Detail ---

async function loadSessionDetail(sessionId) {
    const data = await api(`/api/sessions/${encodeURIComponent(sessionId)}`);

    const header = document.getElementById('session-header');
    const s = data.session;
    header.innerHTML = `
        <span class="back-link" onclick="navigate('browse')">← Back to sessions</span>
        <h1>${escHtml(s.title || 'Untitled Session')}</h1>
        <div class="detail-meta">
            <span>🔧 ${toolDisplayName(s.tool)}</span>
            ${s.model ? `<span>🤖 ${escHtml(s.model)}</span>` : ''}
            ${s.project_path ? `<span>📁 ${escHtml(s.project_path)}</span>` : ''}
            <span>💬 ${s.message_count} messages</span>
            ${s.started_at ? `<span>🕐 ${formatDate(s.started_at)}</span>` : ''}
            <span>💾 ${formatBytes(s.file_size_bytes)}</span>
        </div>
    `;

    const thread = document.getElementById('message-thread');
    if (data.messages.length > 0) {
        thread.innerHTML = data.messages.map(m => messageHtml(m)).join('');
    } else {
        thread.innerHTML = '<p style="color:var(--text-secondary)">No messages in this session.</p>';
    }
}

// --- Search ---

async function doSearch(query) {
    if (!query.trim()) return;
    currentSearchQuery = query;
    currentSearchPage = 1;
    await performSearch();
}

async function performSearch() {
    navigate('search');
    const q = encodeURIComponent(currentSearchQuery);
    const data = await api(`/api/search?q=${q}&page=${currentSearchPage}`);

    document.getElementById('search-title').textContent =
        `Search: "${currentSearchQuery}" (${data.total} results)`;

    const container = document.getElementById('search-results');
    if (data.results.length > 0) {
        container.innerHTML = data.results.map(r => `
            <div class="search-result" onclick="navigate('session','${escAttr(r.session_fk)}')">
                <div class="session-card-header">
                    <span class="session-title">${escHtml(r.session_title || 'Untitled')}</span>
                    <span class="session-tool">${toolDisplayName(r.tool)}</span>
                </div>
                <div class="result-context">${escHtml((r.content_text || '').substring(0, 200))}</div>
                <div class="session-meta">
                    <span>${r.role}</span>
                    ${r.timestamp ? `<span>${formatDate(r.timestamp)}</span>` : ''}
                </div>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<p style="color:var(--text-secondary)">No results found.</p>';
    }

    renderPagination('search-pagination', data, (p) => {
        currentSearchPage = p;
        performSearch();
    });
}

// --- Sync ---

async function triggerSync() {
    const btn = document.getElementById('sync-btn');
    btn.textContent = '⟳ Syncing...';
    btn.disabled = true;
    try {
        const result = await apiPost('/api/sync');
        if (currentView === 'dashboard') loadDashboard();
        if (currentView === 'browse') loadSessions(currentSessionPage);
        alert(`Sync complete!\n${Object.entries(result.results || {}).map(([k,v]) =>
            `${k}: ${v.status} (${v.new} new, ${v.updated} updated)`).join('\n')}`);
    } catch (e) {
        alert('Sync failed: ' + e.message);
    } finally {
        btn.textContent = '⟳ Sync';
        btn.disabled = false;
    }
}

// --- Render helpers ---

function sessionCard(s) {
    const sid = s.id || `${s.tool}:${s.session_id}`;
    return `
        <div class="session-card" onclick="navigate('session','${escAttr(sid)}')">
            <div class="session-card-header">
                <span class="session-title">${escHtml(s.title || 'Untitled Session')}</span>
                <span class="session-tool">${toolDisplayName(s.tool)}</span>
            </div>
            <div class="session-meta">
                ${s.model ? `<span>🤖 ${escHtml(s.model)}</span>` : ''}
                ${s.message_count ? `<span>💬 ${s.message_count} msgs</span>` : ''}
                ${s.started_at ? `<span>🕐 ${formatDate(s.started_at)}</span>` : ''}
                ${s.project_path ? `<span>📁 ${escHtml(truncate(s.project_path, 50))}</span>` : ''}
                <span>💾 ${formatBytes(s.file_size_bytes)}</span>
            </div>
        </div>
    `;
}

function messageHtml(m) {
    const role = m.role || 'system';
    const contentClass = m.content_type === 'thinking' ? 'content-thinking' : '';
    const isLong = (m.content_text || '').length > 500;
    const collapsed = isLong ? 'collapsed' : '';

    return `
        <div class="message role-${escAttr(role)} ${collapsed}" id="msg-${m.id}">
            <div class="message-role">${roleLabel(role, m.content_type)}</div>
            <div class="message-content ${contentClass}">${escHtml(m.content_text || '')}</div>
            ${isLong ? `<button class="expand-btn" onclick="toggleExpand(this)">Show more</button>` : ''}
            ${m.timestamp ? `<div class="message-timestamp">${formatDate(m.timestamp)}</div>` : ''}
            ${m.model ? `<div class="message-timestamp">Model: ${escHtml(m.model)}</div>` : ''}
        </div>
    `;
}

function toggleExpand(btn) {
    const msg = btn.closest('.message');
    if (msg.classList.contains('collapsed')) {
        msg.classList.remove('collapsed');
        btn.textContent = 'Show less';
    } else {
        msg.classList.add('collapsed');
        btn.textContent = 'Show more';
    }
}

function renderPagination(containerId, data, onPageClick) {
    const container = document.getElementById(containerId);
    if (!data.total_pages || data.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';
    html += `<button ${data.page <= 1 ? 'disabled' : ''} onclick="(${onPageClick})(${data.page - 1})">← Prev</button>`;

    const start = Math.max(1, data.page - 3);
    const end = Math.min(data.total_pages, data.page + 3);
    for (let i = start; i <= end; i++) {
        html += `<button class="${i === data.page ? 'active' : ''}" onclick="(${onPageClick})(${i})">${i}</button>`;
    }

    html += `<button ${data.page >= data.total_pages ? 'disabled' : ''} onclick="(${onPageClick})(${data.page + 1})">Next →</button>`;
    container.innerHTML = html;
}

// --- Utilities ---

function escHtml(s) {
    if (!s) return '';
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escAttr(s) {
    if (!s) return '';
    return s.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

function truncate(s, len) {
    if (!s || s.length <= len) return s || '';
    return s.substring(0, len) + '...';
}

function formatDate(d) {
    if (!d) return '';
    try {
        const dt = new Date(d);
        if (isNaN(dt)) return d;
        return dt.toLocaleDateString() + ' ' + dt.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
    } catch { return d; }
}

function formatBytes(b) {
    if (!b) return '0 B';
    const units = ['B','KB','MB','GB'];
    let i = 0;
    let val = b;
    while (val >= 1024 && i < units.length - 1) { val /= 1024; i++; }
    return val.toFixed(i > 0 ? 1 : 0) + ' ' + units[i];
}

const TOOL_DISPLAY_NAMES = {};

function toolDisplayName(tool) {
    if (TOOL_DISPLAY_NAMES[tool]) return TOOL_DISPLAY_NAMES[tool];
    return tool.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function roleLabel(role, contentType) {
    if (contentType === 'thinking') return '💭 Thinking';
    if (contentType === 'tool_use') return '🔧 Tool Use';
    if (role === 'user') return '👤 User';
    if (role === 'assistant') return '🤖 Assistant';
    if (role === 'system') return '⚙️ System';
    return role;
}

// --- Init ---

async function init() {
    // Load tool names for filter dropdown
    const tools = await api('/api/tools');
    const select = document.getElementById('filter-tool');
    tools.forEach(t => {
        TOOL_DISPLAY_NAMES[t.name] = t.display_name;
        const opt = document.createElement('option');
        opt.value = t.name;
        opt.textContent = t.display_name;
        select.appendChild(opt);
    });

    loadDashboard();
}

init();
