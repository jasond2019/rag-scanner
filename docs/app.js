/**
 * RAG Scanner Frontend
 * 使用 HTTP Polling 替代 WebSocket
 */

// API 基础 URL - Vercel 后端地址
const API_URL = 'https://rag-scanner.vercel.app';

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
                    // 保存完整 headers
                    parsedData.headers = data.data.headers;
                } else {
                    parsedAuthSpan.textContent = '(none)';
                    authTokenInput.style.display = 'inline-block';
                    authHint.textContent = '(required)';
                    authHint.className = 'auth-hint auth-needed';
                    parsedData.headers = {};
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
            headers: {},
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
    document.getElementById('progressText').textContent = 'Submitting task...';

    try {
        // Step 1: 创建任务
        const submitResponse = await fetch(`${API_URL}/api/scan/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target_value: parsedData.rawInput,
                target_type: parsedData.inputType,
                param_name: paramName
            })
        });

        const submitData = await submitResponse.json();

        if (submitData.code !== 0) {
            alert('Submit failed: ' + submitData.message);
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('progressContainer').style.display = 'none';
            return;
        }

        currentTaskId = submitData.data.task_id;
        document.getElementById('progressFill').style.width = '30%';
        document.getElementById('progressText').textContent = 'Executing security scan...';

        // Step 2: 执行扫描
        const executeResponse = await fetch(`${API_URL}/api/scan/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentTaskId,
                url: parsedData.url,
                headers: headers,
                param_name: paramName
            })
        });

        const executeData = await executeResponse.json();

        document.getElementById('progressFill').style.width = '100%';
        document.getElementById('progressText').textContent = 'Scan completed!';

        if (executeData.code === 0) {
            // 直接显示结果
            displayResult(executeData.data);
        } else {
            // 执行失败，轮询进度
            startPolling(currentTaskId);
        }

    } catch (error) {
        alert('Network error: ' + error.message);
        document.getElementById('submitBtn').disabled = false;
        document.getElementById('progressContainer').style.display = 'none';
    }
}

// HTTP Polling 进度（备用）
function startPolling(taskId) {
    pollTimer = setInterval(async () => {
        try {
            const res = await fetch(`${API_URL}/api/scan/progress?task_id=${taskId}`);
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
    }, 2000);
}

// 更新进度
function updateProgress(data) {
    document.getElementById('progressFill').style.width = data.progress + '%';
    document.getElementById('progressText').textContent =
        'Checking: ' + data.current_step + ' (' + data.progress + '%)';
}

// 加载结果（备用）
async function loadResult(taskId) {
    try {
        const response = await fetch(`${API_URL}/api/scan/result?task_id=${taskId}`);
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
    document.getElementById('submitBtn').disabled = false;

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

    // 设置报告下载链接（JSON格式）
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.href = `${API_URL}/api/report/download?task_id=${result.task_id || currentTaskId}`;
    downloadBtn.textContent = 'Download JSON Report';
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