// RAG Scanner Admin Dashboard JavaScript

const API_BASE = '/api';

// Section Navigation
function showSection(section) {
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelector(`.nav-tab:nth-child(${getTabIndex(section)})`).classList.add('active');

    document.querySelectorAll('[id$="-section"]').forEach(s => s.style.display = 'none');
    document.getElementById(`${section}-section`).style.display = 'block';

    // Load data for the section
    switch(section) {
        case 'stats': loadStats(); break;
        case 'tasks': loadTasks(); break;
        case 'in_progress': loadInProgress(); break;
        case 'logs': loadLogs(); break;
    }
}

function getTabIndex(section) {
    const tabs = ['stats', 'tasks', 'in_progress', 'logs'];
    return tabs.indexOf(section) + 1;
}

// Statistics
async function loadStats() {
    const statsGrid = document.getElementById('statsGrid');
    const riskGrid = document.getElementById('riskGrid');
    statsGrid.innerHTML = '<div class="loading">Loading...</div>';
    riskGrid.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const resp = await fetch(`${API_BASE}/admin/stats`);
        const data = await resp.json();

        if (data.success) {
            const stats = data.data;
            statsGrid.innerHTML = `
                <div class="stat-card"><div class="stat-value">${stats.total_tasks}</div><div class="stat-label">Total Tasks</div></div>
                <div class="stat-card"><div class="stat-value">${stats.completed_tasks}</div><div class="stat-label">Completed</div></div>
                <div class="stat-card"><div class="stat-value">${stats.in_progress_tasks}</div><div class="stat-label">In Progress</div></div>
                <div class="stat-card"><div class="stat-value">${stats.failed_tasks}</div><div class="stat-label">Failed</div></div>
                <div class="stat-card"><div class="stat-value">${stats.avg_score}</div><div class="stat-label">Avg Score</div></div>
            `;

            const risk = stats.risk_distribution;
            riskGrid.innerHTML = `
                <div class="stat-card"><div class="stat-value">${risk.critical}</div><div class="stat-label">Critical</div></div>
                <div class="stat-card"><div class="stat-value">${risk.high}</div><div class="stat-label">High</div></div>
                <div class="stat-card"><div class="stat-value">${risk.medium}</div><div class="stat-label">Medium</div></div>
                <div class="stat-card"><div class="stat-value">${risk.low}</div><div class="stat-label">Low</div></div>
            `;
        } else {
            statsGrid.innerHTML = `<div class="loading">Error: ${data.error}</div>`;
        }
    } catch (e) {
        statsGrid.innerHTML = `<div class="loading">Error: ${e.message}</div>`;
    }
}

// Tasks List
let currentPage = 0;
const pageSize = 20;

async function loadTasks(page = 0) {
    currentPage = page;
    const tbody = document.getElementById('tasksBody');
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading...</td></tr>';

    try {
        const resp = await fetch(`${API_BASE}/admin/tasks?limit=${pageSize}&offset=${page * pageSize}`);
        const data = await resp.json();

        if (data.success) {
            tbody.innerHTML = data.data.tasks.map(task => `
                <tr>
                    <td>${task.id}</td>
                    <td>${truncate(task.target_value, 50)}</td>
                    <td><span class="status-badge status-${task.status}">${task.status}</span></td>
                    <td>${task.score || '--'}</td>
                    <td>${task.level ? `<span class="level-badge level-${task.level}">${task.level}</span>` : '--'}</td>
                    <td>${formatTime(task.created_at)}</td>
                    <td><button onclick="showDetail('${task.id}')">View</button></td>
                </tr>
            `).join('');

            // Pagination
            renderPagination(data.data.total, page);
        } else {
            tbody.innerHTML = `<tr><td colspan="7" class="loading">Error: ${data.error}</td></tr>`;
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="loading">Error: ${e.message}</td></tr>`;
    }
}

function renderPagination(total, current) {
    const totalPages = Math.ceil(total / pageSize);
    const pagination = document.getElementById('tasksPagination');

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';
    for (let i = 0; i < totalPages; i++) {
        html += `<div class="page-btn ${i === current ? 'active' : ''}" onclick="loadTasks(${i})">${i + 1}</div>`;
    }
    pagination.innerHTML = html;
}

// In Progress Tasks
async function loadInProgress() {
    const tbody = document.getElementById('inProgressBody');
    tbody.innerHTML = '<tr><td colspan="6" class="loading">Loading...</td></tr>';

    try {
        const resp = await fetch(`${API_BASE}/admin/in_progress`);
        const data = await resp.json();

        if (data.success) {
            if (data.data.tasks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="loading">No tasks in progress</td></tr>';
            } else {
                tbody.innerHTML = data.data.tasks.map(task => `
                    <tr>
                        <td>${task.id}</td>
                        <td>${truncate(task.target_value, 50)}</td>
                        <td><span class="status-badge status-${task.status}">${task.status}</span></td>
                        <td>${task.progress}%</td>
                        <td>${task.current_step}</td>
                        <td>${formatTime(task.created_at)}</td>
                    </tr>
                `).join('');
            }
        } else {
            tbody.innerHTML = `<tr><td colspan="6" class="loading">Error: ${data.error}</td></tr>`;
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" class="loading">Error: ${e.message}</td></tr>`;
    }
}

// Audit Logs
async function loadLogs() {
    const tbody = document.getElementById('logsBody');
    tbody.innerHTML = '<tr><td colspan="4" class="loading">Loading...</td></tr>';

    try {
        const resp = await fetch(`${API_BASE}/admin/logs?limit=100`);
        const data = await resp.json();

        if (data.success) {
            tbody.innerHTML = data.data.logs.map(log => `
                <tr>
                    <td>${log.type}</td>
                    <td>${log.task_id}</td>
                    <td>${log.target || log.score || ''}</td>
                    <td>${formatTime(log.timestamp)}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `<tr><td colspan="4" class="loading">Error: ${data.error}</td></tr>`;
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" class="loading">Error: ${e.message}</td></tr>`;
    }
}

// Task Detail
async function showDetail(taskId) {
    const modal = document.getElementById('detailModal');
    const body = document.getElementById('detailBody');
    modal.style.display = 'flex';
    body.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const resp = await fetch(`${API_BASE}/admin/detail?task_id=${taskId}`);
        const data = await resp.json();

        if (data.success) {
            const detail = data.data;
            document.getElementById('detailTitle').textContent = `Task: ${taskId}`;

            body.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-value">${detail.task.score || '--'}</div><div class="stat-label">Score</div></div>
                    <div class="stat-card"><div class="stat-value">${detail.total_vulnerabilities}</div><div class="stat-label">Vulnerabilities</div></div>
                    <div class="stat-card"><div class="stat-value">${detail.critical_count}</div><div class="stat-label">Critical</div></div>
                    <div class="stat-card"><div class="stat-value">${detail.high_count}</div><div class="stat-label">High</div></div>
                </div>

                <h3 class="section-title">Task Info</h3>
                <table class="task-table">
                    <tr><th>Target Type</th><td>${detail.task.target_type}</td></tr>
                    <tr><th>Target Value</th><td>${detail.task.target_value}</td></tr>
                    <tr><th>Status</th><td><span class="status-badge status-${detail.task.status}">${detail.task.status}</span></td></tr>
                    <tr><th>Risk Level</th><td>${detail.task.level ? `<span class="level-badge level-${detail.task.level}">${detail.task.level}</span>` : '--'}</td></tr>
                    <tr><th>Created</th><td>${formatTime(detail.task.created_at)}</td></tr>
                </table>

                <h3 class="section-title">Vulnerabilities</h3>
                <div class="vuln-list">
                    ${detail.vulnerabilities.map(v => `
                        <div class="vuln-card">
                            <div class="vuln-card-header">
                                <span class="vuln-card-name">${v.name}</span>
                                <span class="level-badge level-${v.severity}">${v.severity}</span>
                            </div>
                            <div class="vuln-card-desc">${v.description || 'No description'}</div>
                            ${v.suggestion ? `<div class="vuln-card-desc"><strong>Suggestion:</strong> ${v.suggestion}</div>` : ''}
                        </div>
                    `).join('')}
                </div>

                <div style="margin-top: 20px;">
                    <button class="refresh-btn" onclick="downloadReport('${taskId}')">Download Report</button>
                </div>
            `;
        } else {
            body.innerHTML = `<div class="loading">Error: ${data.error}</div>`;
        }
    } catch (e) {
        body.innerHTML = `<div class="loading">Error: ${e.message}</div>`;
    }
}

function closeDetail() {
    document.getElementById('detailModal').style.display = 'none';
}

function downloadReport(taskId) {
    window.open(`${API_BASE}/report/download?task_id=${taskId}`, '_blank');
}

// Helper Functions
function truncate(str, len) {
    if (!str) return '--';
    return str.length > len ? str.substring(0, len) + '...' : str;
}

function formatTime(isoStr) {
    if (!isoStr) return '--';
    try {
        const d = new Date(isoStr);
        return d.toLocaleString();
    } catch {
        return isoStr;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
});