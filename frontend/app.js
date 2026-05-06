/**
 * RAG Scanner Frontend
 * 使用 HTTP Polling 替代 WebSocket
 */

// API 基础 URL - 部署到 Vercel 后修改
const API_URL = window.RAG_SCANNER_API_URL || 'https://rag-scanner-api.vercel.app';
// 本地开发时使用: 'http://localhost:3000'

let currentTaskId = null;
let parsedData = null;
let debounceTimer = null;
let pollTimer = null;

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
            const res = await fetch(`${API_URL}/api/scan/parse_curl`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ curl: input })
            });
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
                    authHint.textContent = '(parsed from curl)';
                    authHint.className = 'auth-hint auth-from-curl';
                } else {
                    parsedAuthSpan.textContent = '(none)';
                    authTokenInput.style.display = 'inline-block';
                    authHint.textContent = '(required)';
                    authHint.className = 'auth-hint auth-needed';
                }

                previewSection.style.display = 'block';
            } else {
                errorMsg.textContent = 'curl parse failed: ' + data.message;
                errorMsg.style.display = 'block';
                previewSection.style.display = 'none';
            }
        } catch (e) {
            errorMsg.textContent = 'Request failed: ' + e.message;
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
            auth_header: null
        };

        document.getElementById('parsedUrl').textContent = input;
        document.getElementById('parsedMethod').textContent = 'POST';
        document.getElementById('paramSelect').value = 'query';
        document.getElementById('customParam').style.display = 'none';

        // URL 需要手动输入认证
        document.getElementById('parsedAuth').textContent = '(config needed)';
        document.getElementById('authToken').style.display = 'inline-block';
        document.getElementById('authToken').value = '';
        document.getElementById('authHint').textContent = '(no auth detected)';
        document.getElementById('authHint').className = 'auth-hint auth-needed';

        previewSection.style.display = 'block';
    }
    // 无效输入
    else {
        errorMsg.textContent = 'Please enter valid URL or curl command';
        errorMsg.style.display = 'block';
        previewSection.style.display = 'none';
        parsedData = null;
    }
}

// 开始扫描
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
            alert('Please enter custom parameter name');
            return;
        }
    }

    // 获取认证 token (如果是 URL 模式)
    let authToken = null;
    if (parsedData.inputType === 'url') {
        authToken = document.getElementById('authToken').value.trim();
    }

    // 重置 UI
    document.getElementById('submitBtn').disabled = true;
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('resultContainer').style.display = 'none';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = 'Submitting task...';

    try {
        const requestBody = {
            target_value: parsedData.rawInput,
            target_type: parsedData.inputType,
            param_name: paramName,
            step: 1
        };

        // URL 模式添加认证
        if (parsedData.inputType === 'url' && authToken) {
            requestBody.auth_token = authToken;
        }

        const response = await fetch(`${API_URL}/api/scan/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.code === 0) {
            currentTaskId = data.data.task_id;
            document.getElementById('progressText').textContent = 'Scan in progress...';
            // 开始轮询进度
            startPolling(currentTaskId);
        } else {
            alert('Submit failed: ' + data.message);
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('progressContainer').style.display = 'none';
        }
    } catch (error) {
        alert('Network error: ' + error.message);
        document.getElementById('submitBtn').disabled = false;
        document.getElementById('progressContainer').style.display = 'none';
    }
}

// HTTP Polling 进度
function startPolling(taskId) {
    pollTimer = setInterval(async () => {
        try {
            const res = await fetch(`${API_URL}/api/scan/${taskId}/progress`);
            const data = await res.json();

            if (data.code === 0) {
                updateProgress(data.data);

                if (data.data.status === 'completed') {
                    clearInterval(pollTimer);
                    document.getElementById('submitBtn').disabled = false;
                    loadResult(taskId);
                } else if (data.data.status === 'failed') {
                    clearInterval(pollTimer);
                    document.getElementById('progressText').textContent = 'Scan failed';
                    document.getElementById('submitBtn').disabled = false;
                }
            }
        } catch (e) {
            console.error('Polling error:', e);
        }
    }, 2000); // 2秒轮询
}

// 更新进度
function updateProgress(data) {
    document.getElementById('progressFill').style.width = data.progress + '%';
    document.getElementById('progressText').textContent =
        'Checking: ' + data.current_step + ' (' + data.progress + '%)';
}

// 加载结果
async function loadResult(taskId) {
    try {
        const response = await fetch(`${API_URL}/api/scan/${taskId}/result`);
        const data = await response.json();

        if (data.code === 0) {
            displayResult(data.data);
        }
    } catch (error) {
        console.error('Load result failed:', error);
    }
}

// 显示结果
function displayResult(result) {
    document.getElementById('resultContainer').style.display = 'block';
    document.getElementById('progressContainer').style.display = 'none';

    const scoreEl = document.getElementById('scoreNumber');
    const levelEl = document.getElementById('scoreLevel');

    scoreEl.textContent = result.score;
    scoreEl.style.color = getScoreColor(result.score);

    const levelText = { high: 'High Risk', medium: 'Medium Risk', low: 'Low Risk' };
    levelEl.textContent = levelText[result.level] || 'Unknown';

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
        vulnContainer.innerHTML = '<p style="text-align: center; color: #666;">&#127881; No security vulnerabilities found!</p>';
    }

    // 设置报告下载链接
    document.getElementById('downloadBtn').href = `${API_URL}/api/report/generate?task_id=${result.task_id || currentTaskId}`;
}

// 工具函数
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
    const map = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };
    return map[severity] || severity;
}