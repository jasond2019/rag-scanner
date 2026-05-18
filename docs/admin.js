// RAG Scanner 管理后台 JavaScript

const API_BASE = 'https://rag-scanner.vercel.app/api';

// 区域导航
function showSection(section) {
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    document.querySelector(`.nav-tab:nth-child(${getTabIndex(section)})`).classList.add('active');

    document.querySelectorAll('[id$="-section"]').forEach(s => s.style.display = 'none');
    document.getElementById(`${section}-section`).style.display = 'block';

    // 加载区域数据
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

// 统计数据
async function loadStats() {
    const statsGrid = document.getElementById('statsGrid');
    const riskGrid = document.getElementById('riskGrid');
    statsGrid.innerHTML = '<div class="loading">加载中...</div>';
    riskGrid.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const resp = await fetch(`${API_BASE}/admin/stats`);
        const data = await resp.json();

        if (data.success) {
            const stats = data.data;
            statsGrid.innerHTML = `
                <div class="stat-card"><div class="stat-value">${stats.total_tasks}</div><div class="stat-label">总任务数</div></div>
                <div class="stat-card"><div class="stat-value">${stats.completed_tasks}</div><div class="stat-label">已完成</div></div>
                <div class="stat-card"><div class="stat-value">${stats.in_progress_tasks}</div><div class="stat-label">进行中</div></div>
                <div class="stat-card"><div class="stat-value">${stats.failed_tasks}</div><div class="stat-label">失败</div></div>
                <div class="stat-card"><div class="stat-value">${stats.avg_score}</div><div class="stat-label">平均评分</div></div>
            `;

            const risk = stats.risk_distribution;
            riskGrid.innerHTML = `
                <div class="stat-card"><div class="stat-value">${risk.critical}</div><div class="stat-label">严重</div></div>
                <div class="stat-card"><div class="stat-value">${risk.high}</div><div class="stat-label">高危</div></div>
                <div class="stat-card"><div class="stat-value">${risk.medium}</div><div class="stat-label">中危</div></div>
                <div class="stat-card"><div class="stat-value">${risk.low}</div><div class="stat-label">低危</div></div>
            `;
        } else {
            statsGrid.innerHTML = `<div class="loading">错误: ${data.error}</div>`;
        }
    } catch (e) {
        statsGrid.innerHTML = `<div class="loading">错误: ${e.message}</div>`;
    }
}

// 任务列表
let currentPage = 0;
const pageSize = 20;

async function loadTasks(page = 0) {
    currentPage = page;
    const tbody = document.getElementById('tasksBody');
    tbody.innerHTML = '<tr><td colspan="8" class="loading">加载中...</td></tr>';

    try {
        const resp = await fetch(`${API_BASE}/admin/tasks?limit=${pageSize}&offset=${page * pageSize}`);
        const data = await resp.json();

        if (data.success) {
            tbody.innerHTML = data.data.tasks.map(task => `
                <tr>
                    <td>${task.id}</td>
                    <td><span class="user-id-cell" title="${task.user_id || 'anonymous'}">${truncate(task.user_id || 'anonymous', 20)}</span></td>
                    <td>${truncate(task.target_value, 50)}</td>
                    <td><span class="status-badge status-${task.status}">${getStatusText(task.status)}</span></td>
                    <td>${task.score || '--'}</td>
                    <td>${task.level ? `<span class="level-badge level-${task.level}">${getLevelText(task.level)}</span>` : '--'}</td>
                    <td>${formatTime(task.created_at)}</td>
                    <td><button class="refresh-btn" onclick="showDetail('${task.id}')">查看</button></td>
                </tr>
            `).join('');

            // 分页
            renderPagination(data.data.total, page);
        } else {
            tbody.innerHTML = `<tr><td colspan="8" class="loading">错误: ${data.error}</td></tr>`;
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="8" class="loading">错误: ${e.message}</td></tr>`;
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

// 进行中任务
async function loadInProgress() {
    const tbody = document.getElementById('inProgressBody');
    tbody.innerHTML = '<tr><td colspan="6" class="loading">加载中...</td></tr>';

    try {
        const resp = await fetch(`${API_BASE}/admin/in_progress`);
        const data = await resp.json();

        if (data.success) {
            if (data.data.tasks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="loading">没有进行中的任务</td></tr>';
            } else {
                tbody.innerHTML = data.data.tasks.map(task => `
                    <tr>
                        <td>${task.id}</td>
                        <td>${truncate(task.target_value, 50)}</td>
                        <td><span class="status-badge status-${task.status}">${getStatusText(task.status)}</span></td>
                        <td>${task.progress}%</td>
                        <td>${task.current_step}</td>
                        <td>${formatTime(task.created_at)}</td>
                    </tr>
                `).join('');
            }
        } else {
            tbody.innerHTML = `<tr><td colspan="6" class="loading">错误: ${data.error}</td></tr>`;
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" class="loading">错误: ${e.message}</td></tr>`;
    }
}

// 审计日志
async function loadLogs() {
    const tbody = document.getElementById('logsBody');
    tbody.innerHTML = '<tr><td colspan="4" class="loading">加载中...</td></tr>';

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
            tbody.innerHTML = `<tr><td colspan="4" class="loading">错误: ${data.error}</td></tr>`;
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" class="loading">错误: ${e.message}</td></tr>`;
    }
}

// 任务详情
async function showDetail(taskId) {
    const modal = document.getElementById('detailModal');
    const body = document.getElementById('detailBody');
    modal.style.display = 'flex';
    body.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const resp = await fetch(`${API_BASE}/admin/detail?task_id=${taskId}`);
        const data = await resp.json();

        if (data.success) {
            const detail = data.data;
            document.getElementById('detailTitle').textContent = `任务: ${taskId}`;

            body.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-value">${detail.task.score || '--'}</div><div class="stat-label">评分</div></div>
                    <div class="stat-card"><div class="stat-value">${detail.total_vulnerabilities}</div><div class="stat-label">漏洞数</div></div>
                    <div class="stat-card"><div class="stat-value">${detail.critical_count}</div><div class="stat-label">严重</div></div>
                    <div class="stat-card"><div class="stat-value">${detail.high_count}</div><div class="stat-label">高危</div></div>
                </div>

                <h3 class="section-title">任务信息</h3>
                <table class="task-table">
                    <tr><th>目标类型</th><td>${detail.task.target_type}</td></tr>
                    <tr><th>目标地址</th><td>${detail.task.target_value}</td></tr>
                    <tr><th>状态</th><td><span class="status-badge status-${detail.task.status}">${getStatusText(detail.task.status)}</span></td></tr>
                    <tr><th>风险等级</th><td>${detail.task.level ? `<span class="level-badge level-${detail.task.level}">${getLevelText(detail.task.level)}</span>` : '--'}</td></tr>
                    <tr><th>创建时间</th><td>${formatTime(detail.task.created_at)}</td></tr>
                </table>

                <h3 class="section-title">漏洞列表</h3>
                <div class="vuln-list">
                    ${detail.vulnerabilities.map(v => `
                        <div class="vuln-card">
                            <div class="vuln-card-header">
                                <span class="vuln-card-name">${v.name}</span>
                                <span class="level-badge level-${v.severity}">${getLevelText(v.severity)}</span>
                            </div>
                            <div class="vuln-card-desc">${v.description || '无描述'}</div>
                            ${v.suggestion ? `<div class="vuln-card-desc"><strong>建议:</strong> ${v.suggestion}</div>` : ''}
                        </div>
                    `).join('')}
                </div>

                <div style="margin-top: 20px;">
                    <button class="refresh-btn" onclick="downloadReport('${taskId}')">下载报告</button>
                </div>
            `;
        } else {
            body.innerHTML = `<div class="loading">错误: ${data.error}</div>`;
        }
    } catch (e) {
        body.innerHTML = `<div class="loading">错误: ${e.message}</div>`;
    }
}

function closeDetail() {
    document.getElementById('detailModal').style.display = 'none';
}

function downloadReport(taskId) {
    window.open(`${API_BASE}/report/download?task_id=${taskId}`, '_blank');
}

// 辅助函数
function truncate(str, len) {
    if (!str) return '--';
    return str.length > len ? str.substring(0, len) + '...' : str;
}

function formatTime(isoStr) {
    if (!isoStr) return '--';
    try {
        const d = new Date(isoStr);
        return d.toLocaleString('zh-CN');
    } catch {
        return isoStr;
    }
}

function getStatusText(status) {
    const map = {
        'completed': '已完成',
        'running': '进行中',
        'queued': '排队中',
        'failed': '失败'
    };
    return map[status] || status;
}

function getLevelText(level) {
    const map = {
        'critical': '严重',
        'high': '高危',
        'medium': '中危',
        'low': '低危'
    };
    return map[level] || level;
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
});

// ==================== 用户过滤功能 ====================

/**
 * 按输入的用户 ID 过滤任务
 */
async function filterByUser() {
    const userId = document.getElementById('userFilterInput').value.trim();
    if (!userId) {
        alert('请输入用户 ID');
        return;
    }

    const tbody = document.getElementById('tasksBody');
    tbody.innerHTML = '<tr><td colspan="8" class="loading">查询中...</td></tr>';

    try {
        const resp = await fetch(`${API_BASE}/admin/history?user_id=${encodeURIComponent(userId)}`);
        const data = await resp.json();

        if (data.success) {
            const tasks = data.data.tasks;
            if (tasks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="loading">该用户暂无扫描记录</td></tr>';
            } else {
                tbody.innerHTML = tasks.map(task => `
                    <tr>
                        <td>${task.id}</td>
                        <td><span class="user-id-cell" title="${userId}">${truncate(userId, 20)}</span></td>
                        <td>${truncate(task.target_value, 50)}</td>
                        <td><span class="status-badge status-${task.status}">${getStatusText(task.status)}</span></td>
                        <td>${task.score || '--'}</td>
                        <td>${task.level ? `<span class="level-badge level-${task.level}">${getLevelText(task.level)}</span>` : '--'}</td>
                        <td>${formatTime(task.created_at)}</td>
                        <td><button class="refresh-btn" onclick="showDetail('${task.id}')">查看</button></td>
                    </tr>
                `).join('');
            }
            // 清除分页（用户过滤不分页）
            document.getElementById('tasksPagination').innerHTML = '';
        } else {
            tbody.innerHTML = `<tr><td colspan="8" class="loading">错误: ${data.error}</td></tr>`;
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="8" class="loading">错误: ${e.message}</td></tr>`;
    }
}

/**
 * 查看当前用户的扫描历史
 * - 从 localStorage 获取当前用户 ID（与 app.js 共享）
 * - 调用 history 接口获取该用户的所有扫描记录
 */
async function showMyHistory() {
    // 从 localStorage 获取用户 ID（与 app.js 共享）
    let userId = localStorage.getItem('rag_user_id');

    if (!userId) {
        alert('您还没有进行过扫描，暂无历史记录。\n\n请先在主页进行一次扫描，系统会自动生成用户 ID。');
        return;
    }

    // 显示用户 ID
    document.getElementById('userFilterInput').value = userId;

    // 查询历史
    await filterByUser();
}