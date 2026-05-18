/**
 * RAG Scanner Frontend
 * HTTP Polling 进度更新
 */

// API 基础 URL - Vercel 后端地址
const API_URL = 'https://rag-scanner.vercel.app';

// 超时配置（Vercel Serverless 冷启动可能需要较长时间）
const FETCH_TIMEOUT = 30000; // 30秒超时
const POLL_INTERVAL = 2000;  // 2秒轮询间隔
const MAX_POLL_TIME = 120000; // 最大轮询时间 120秒

let currentTaskId = null;
let parsedData = null;
let debounceTimer = null;
let pollTimer = null;

// ===== 用户 ID 管理 =====
/**
 * 获取或创建用户 ID
 * - 首次访问时生成，存储在 localStorage
 * - 格式: user_时间戳_随机字符串
 * - 同一设备、同一浏览器持久保存
 */
function getUserId() {
    let userId = localStorage.getItem('rag_user_id');
    if (!userId) {
        userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('rag_user_id', userId);
        console.log('[RAG Scanner] Created new user ID:', userId);
    }
    return userId;
}

// ===== 带超时的 fetch =====
async function fetchWithTimeout(url, options = {}, timeout = FETCH_TIMEOUT) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('请求超时，Vercel 服务可能正在冷启动，请稍后重试');
        }
        throw error;
    }
}

// 输入框变化时自动解析
document.getElementById('inputBox').addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => parseInput(e.target.value), 300);
});

// 参数选择变化
document.getElementById('paramSelect').addEventListener('change', (e) => {
    const customInput = document.getElementById('customParam');
    customInput.style.display = e.target.value === 'custom' ? 'inline-block' : 'none';
});

// 解析输入内容
async function parseInput(input) {
    input = input.trim();
    const previewSection = document.getElementById('previewSection');
    const errorMsg = document.getElementById('errorMsg');
    const inputTypeBadge = document.getElementById('inputTypeBadge');

    errorMsg.style.display = 'none';

    if (!input) {
        previewSection.style.display = 'none';
        parsedData = null;
        return;
    }

    // curl 命令
    if (input.toLowerCase().startsWith('curl ')) {
        inputTypeBadge.textContent = 'curl';
        inputTypeBadge.className = 'input-type-badge curl';

        try {
            const res = await fetchWithTimeout(`${API_URL}/api/scan/parse_curl`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ curl: input })
            }, FETCH_TIMEOUT);
            const data = await res.json();

            if (data.code === 0) {
                parsedData = data.data;
                parsedData.inputType = 'curl';
                parsedData.rawInput = input;

                document.getElementById('parsedUrl').textContent = data.data.url;
                document.getElementById('parsedMethod').textContent = data.data.method;

                // 设置参数名
                const paramSelect = document.getElementById('paramSelect');
                const paramOptions = paramSelect.options;
                let found = false;
                for (let i = 0; i < paramOptions.length; i++) {
                    if (paramOptions[i].value === data.data.param_name) {
                        paramSelect.value = data.data.param_name;
                        found = true;
                        break;
                    }
                }
                if (!found && data.data.param_name) {
                    paramSelect.value = 'custom';
                    document.getElementById('customParam').value = data.data.param_name;
                    document.getElementById('customParam').style.display = 'inline-block';
                }

                // 认证信息
                const authTokenInput = document.getElementById('authToken');
                const parsedAuthSpan = document.getElementById('parsedAuth');
                const authHint = document.getElementById('authHint');

                if (data.data.auth_header) {
                    parsedAuthSpan.textContent = data.data.auth_header;
                    authTokenInput.style.display = 'none';
                    authHint.textContent = '(已从 curl 解析)';
                    authHint.className = 'auth-hint auth-from-curl';
                    // 保存完整 headers
                    parsedData.headers = data.data.headers;
                } else {
                    parsedAuthSpan.textContent = '(无)';
                    authTokenInput.style.display = 'inline-block';
                    authHint.textContent = '(需手动输入)';
                    authHint.className = 'auth-hint auth-needed';
                    parsedData.headers = {};
                }

                previewSection.style.display = 'block';
            } else {
                errorMsg.textContent = 'curl 解析失败: ' + data.message;
                errorMsg.style.display = 'block';
                previewSection.style.display = 'none';
            }
        } catch (e) {
            errorMsg.textContent = '解析请求失败: ' + e.message;
            errorMsg.style.display = 'block';
            previewSection.style.display = 'none';
        }
    }
    // URL
    else if (input.startsWith('http://') || input.startsWith('https://')) {
        inputTypeBadge.textContent = 'URL';
        inputTypeBadge.className = 'input-type-badge url';

        parsedData = {
            url: input,
            method: 'POST',
            inputType: 'url',
            rawInput: input,
            param_name: 'query',
            headers: {},
            auth_header: null
        };

        document.getElementById('parsedUrl').textContent = input;
        document.getElementById('parsedMethod').textContent = 'POST';
        document.getElementById('paramSelect').value = 'query';
        document.getElementById('customParam').style.display = 'none';

        // URL 需要手动输入认证
        document.getElementById('parsedAuth').textContent = '(需配置)';
        document.getElementById('authToken').style.display = 'inline-block';
        document.getElementById('authToken').value = '';
        document.getElementById('authHint').textContent = '(未检测到认证)';
        document.getElementById('authHint').className = 'auth-hint auth-needed';

        previewSection.style.display = 'block';
    }
    // 无效输入
    else {
        errorMsg.textContent = '请输入有效的 URL 或 curl 命令';
        errorMsg.style.display = 'block';
        previewSection.style.display = 'none';
        parsedData = null;
    }
}

// ===== 开始扫描（轮询模式） =====
async function startScan() {
    if (!parsedData) {
        await parseInput(document.getElementById('inputBox').value);
        if (!parsedData) return;
    }

    // 获取最终参数名
    let paramName = document.getElementById('paramSelect').value;
    if (paramName === 'custom') {
        paramName = document.getElementById('customParam').value.trim();
        if (!paramName) {
            alert('请输入自定义参数名');
            return;
        }
    }

    // 获取认证 token
    let headers = parsedData.headers || {};
    if (parsedData.inputType === 'url') {
        const authToken = document.getElementById('authToken').value.trim();
        if (authToken) {
            headers['Authorization'] = authToken.startsWith('Bearer ') ? authToken : `Bearer ${authToken}`;
        }
    }

    // 重置 UI
    document.getElementById('submitBtn').disabled = true;
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('resultContainer').style.display = 'none';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = '提交任务...';

    // 清除之前可能存在的错误显示
    const errorBox = document.getElementById('errorBox');
    if (errorBox) {
        errorBox.style.display = 'none';
    }

    try {
        // ===== Step 1: 提交任务 =====
        const userId = getUserId();  // 获取用户 ID

        const submitResponse = await fetchWithTimeout(`${API_URL}/api/scan/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target_value: parsedData.rawInput,
                target_type: parsedData.inputType,
                param_name: paramName,
                user_id: userId  // 发送用户 ID
            })
        }, FETCH_TIMEOUT);

        const submitData = await submitResponse.json();

        if (submitData.code !== 0) {
            showError('提交失败: ' + submitData.message);
            return;
        }

        currentTaskId = submitData.data.task_id;

        // ===== Step 2: 启动扫描（不等待返回） =====
        fetchWithTimeout(`${API_URL}/api/scan/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentTaskId,
                url: parsedData.url,
                headers: headers,
                param_name: paramName
            })
        }, FETCH_TIMEOUT).catch(e => {
            console.error('Execute request error:', e);
            // 不中断流程，继续轮询
        });

        // ===== Step 3: 开始轮询进度 =====
        document.getElementById('progressText').textContent = '扫描启动中...';
        startPolling(currentTaskId);

    } catch (error) {
        showError('网络错误: ' + error.message);
    }
}

// ===== 轮询进度 =====
function startPolling(taskId) {
    // 清除之前的轮询
    if (pollTimer) {
        clearInterval(pollTimer);
    }

    let pollCount = 0;
    const maxPolls = MAX_POLL_TIME / POLL_INTERVAL;  // 最大轮询次数

    pollTimer = setInterval(async () => {
        pollCount++;

        if (pollCount > maxPolls) {
            clearInterval(pollTimer);
            showError('扫描超时（120秒），请重试或检查目标服务器');
            return;
        }

        try {
            const response = await fetchWithTimeout(`${API_URL}/api/scan/progress?task_id=${taskId}`, {}, FETCH_TIMEOUT);
            const data = await response.json();

            if (data.code === 0) {
                updateProgressUI(data.data);

                // 检查状态
                if (data.data.status === 'completed') {
                    clearInterval(pollTimer);
                    document.getElementById('submitBtn').disabled = false;
                    loadResult(taskId);
                } else if (data.data.status === 'failed') {
                    clearInterval(pollTimer);
                    showError(data.data.error || '扫描失败');
                }
            } else {
                clearInterval(pollTimer);
                showError(data.message || '查询进度失败');
            }
        } catch (e) {
            console.error('轮询错误:', e);
            // 单次失败不中断，继续轮询
        }
    }, POLL_INTERVAL); // 每 2 秒轮询
}

// ===== 更新进度 UI =====
function updateProgressUI(data) {
    const fill = document.getElementById('progressFill');
    const text = document.getElementById('progressText');

    // 更新进度条宽度
    fill.style.width = data.progress + '%';

    // 步骤图标映射
    const stepIcons = {
        '初始化': '⚙️',
        '加载': '📚',
        '规则': '📚',
        '提示词注入检测': '💉',
        '越狱攻击检测': '🔓',
        '数据泄露检测': '📉',
        '权限绕过检测': '🔓',
        '隐私数据检测': '🔒',
        '敏感内容检测': '⚠️',
        '计算': '📊',
        '保存': '💾',
        '完成': '✅',
        '扫描完成': '✅',
        'waiting': '⏳'
    };

    // 获取图标
    let icon = '🔍';
    for (const key in stepIcons) {
        if (data.current_step && data.current_step.includes(key)) {
            icon = stepIcons[key];
            break;
        }
    }

    text.textContent = `${icon} ${data.current_step} (${data.progress}%)`;

    // 进度条颜色变化
    if (data.progress >= 100) {
        fill.style.background = 'linear-gradient(90deg, #38a169 0%, #68d391 100%)';
    } else if (data.progress >= 50) {
        fill.style.background = 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)';
    }
}

// ===== 显示错误 =====
function showError(errorInfo) {
    // 解析错误信息
    let message = '未知错误';
    let suggestion = '';

    if (typeof errorInfo === 'string') {
        message = errorInfo;
    } else if (errorInfo.error) {
        message = errorInfo.error;
    }

    // 根据错误类型给出建议
    if (message.includes('Database')) {
        suggestion = '数据库连接失败，请稍后重试';
    } else if (message.includes('timeout') || message.includes('超时')) {
        suggestion = '扫描超时，可能是目标服务器响应慢';
    } else if (message.includes('connection') || message.includes('连接')) {
        suggestion = '无法连接目标服务器，请检查 URL 是否正确';
    } else {
        suggestion = '请检查输入是否正确，或联系技术支持';
    }

    // 隐藏进度条
    document.getElementById('progressContainer').style.display = 'none';

    // 显示错误区域
    let errorBox = document.getElementById('errorBox');
    if (!errorBox) {
        const container = document.querySelector('.container');
        errorBox = document.createElement('div');
        errorBox.id = 'errorBox';
        errorBox.className = 'error-container';
        errorBox.style.cssText = 'display:block; padding:30px; background:#fff5f5; border-radius:12px; margin-bottom:20px; border-left:4px solid #e53e3e;';
        container.insertBefore(errorBox, document.getElementById('resultContainer'));
    }

    errorBox.style.display = 'block';
    errorBox.innerHTML = `
        <div style="text-align:center;">
            <div style="font-size:48px; color:#e53e3e;">❌</div>
            <h3 style="color:#e53e3e; margin-top:10px;">扫描失败</h3>
            <p style="color:#666; margin-top:10px;"><strong>错误原因:</strong> ${escapeHtml(message)}</p>
            <p style="color:#666; margin-top:5px;"><strong>建议:</strong> ${escapeHtml(suggestion)}</p>
            <button class="btn" style="margin-top:20px;" onclick="retryScan()">重新扫描</button>
        </div>
    `;

    // 启用按钮
    document.getElementById('submitBtn').disabled = false;
}

// ===== 重新扫描 =====
function retryScan() {
    const errorBox = document.getElementById('errorBox');
    if (errorBox) {
        errorBox.style.display = 'none';
    }
    startScan();
}

// ===== 加载结果 =====
async function loadResult(taskId) {
    try {
        const response = await fetchWithTimeout(`${API_URL}/api/scan/result?task_id=${taskId}`, {}, FETCH_TIMEOUT);
        const data = await response.json();

        if (data.code === 0) {
            displayResult(data.data);
        } else {
            showError('加载结果失败: ' + data.message);
        }
    } catch (error) {
        showError('加载结果失败: ' + error.message);
    }
}

// ===== 显示结果 =====
function displayResult(result) {
    document.getElementById('resultContainer').style.display = 'block';
    document.getElementById('progressContainer').style.display = 'none';
    document.getElementById('submitBtn').disabled = false;

    const scoreEl = document.getElementById('scoreNumber');
    const levelEl = document.getElementById('scoreLevel');

    scoreEl.textContent = result.score;
    scoreEl.style.color = getScoreColor(result.score);

    const levelText = { high: '高风险', medium: '中风险', low: '低风险' };
    levelEl.textContent = levelText[result.level] || '未知风险';

    const vulnContainer = document.getElementById('vulnerabilities');
    vulnContainer.innerHTML = '';

    if (result.vulnerabilities && result.vulnerabilities.length > 0) {
        result.vulnerabilities.forEach(vuln => {
            const vulnEl = document.createElement('div');
            vulnEl.className = 'vuln-item ' + vuln.severity;
            vulnEl.innerHTML =
                '<div class="vuln-header">' +
                    '<span class="vuln-name">' + escapeHtml(vuln.name) + '</span>' +
                    '<span class="vuln-severity severity-' + escapeHtml(vuln.severity) + '">' +
                        getSeverityText(vuln.severity) +
                    '</span>' +
                '</div>' +
                '<div>' + escapeHtml(vuln.description) + '</div>' +
                '<div style="margin-top: 8px; color: #666; font-size: 14px;">' +
                    '&#128161; ' + escapeHtml(vuln.suggestion) +
                '</div>';
            vulnContainer.appendChild(vulnEl);
        });
    } else {
        vulnContainer.innerHTML = '<p style="text-align: center; color: #666;">&#127881; 未发现安全漏洞!</p>';
    }

    // 设置报告下载按钮 - PDF 格式
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.onclick = function(e) {
        e.preventDefault();
        downloadPDFReport(result.task_id || currentTaskId);
    };
    downloadBtn.textContent = '下载 PDF 报告';
    downloadBtn.href = '#';
}

// ===== 工具函数 =====
function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function getScoreColor(score) {
    if (score >= 90) return '#38a169';
    if (score >= 70) return '#d69e2e';
    return '#e53e3e';
}

function getSeverityText(severity) {
    const map = { critical: '严重', high: '高危', medium: '中危', low: '低危' };
    return map[severity] || severity;
}

// ===== 用户历史记录 =====
/**
 * 加载当前用户的扫描历史记录
 * - 从 localStorage 获取 user_id
 * - 调用 /api/admin/history 接口
 * - 显示在页面下方的历史记录区域
 */
async function loadMyHistory() {
    const userId = getUserId();
    const historyList = document.getElementById('historyList');

    try {
        const resp = await fetch(`${API_URL}/api/admin/history?user_id=${userId}`);
        const data = await resp.json();

        if (data.success && data.data.tasks.length > 0) {
            const tasks = data.data.tasks;
            historyList.innerHTML = tasks.map(task => `
                <div class="history-item" onclick="viewHistoryTask('${task.id}')">
                    <div class="history-info">
                        <span class="history-target">${escapeHtml(task.target_value.substring(0, 60))}${task.target_value.length > 60 ? '...' : ''}</span>
                        <span class="history-time">${formatHistoryTime(task.created_at)}</span>
                    </div>
                    <div class="history-result">
                        <span class="history-score" style="color: ${getScoreColor(task.score ?? 100)}">${task.score ?? '--'}分</span>
                        <span class="history-status status-${task.status}">${getStatusText(task.status)}</span>
                    </div>
                </div>
            `).join('');
        } else {
            historyList.innerHTML = '<p class="empty-history">暂无扫描记录，开始您的第一次扫描吧！</p>';
        }
    } catch (e) {
        historyList.innerHTML = `<p class="error-text">加载失败: ${e.message}</p>`;
    }
}

/**
 * 点击历史记录项查看详情
 */
async function viewHistoryTask(taskId) {
    // 显示进度区域
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('progressFill').style.width = '100%';
    document.getElementById('progressText').textContent = '加载历史结果...';

    try {
        // 查询结果
        const resp = await fetch(`${API_URL}/api/scan/result?task_id=${taskId}`);
        const data = await resp.json();

        if (data.code === 0) {
            // 显示结果
            displayResult(data.data);
            currentTaskId = taskId;
        } else {
            showError('加载失败: ' + data.message);
        }
    } catch (e) {
        showError('网络错误: ' + e.message);
    }
}

/**
 * 格式化历史记录时间
 */
function formatHistoryTime(isoStr) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr);
        return d.toLocaleDateString('zh-CN') + ' ' + d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    } catch {
        return isoStr;
    }
}

/**
 * 获取状态文本
 */
function getStatusText(status) {
    const map = { completed: '已完成', running: '进行中', queued: '排队中', failed: '失败' };
    return map[status] || status;
}

// ===== 页面初始化 =====
// 页面加载完成后加载历史记录
document.addEventListener('DOMContentLoaded', () => {
    loadMyHistory();
});