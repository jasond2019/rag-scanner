"""
API 入口 - 提交扫描任务
（简化版：暂不使用数据库，直接返回任务 ID）
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)


@app.route('/api/scan/submit', methods=['POST', 'GET', 'OPTIONS'])
def submit_scan():
    """提交扫描任务"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    if request.method == 'GET':
        return jsonify({
            'code': 0,
            'message': 'submit API is running',
            'usage': 'POST with {"target_value": "curl or URL"}'
        })

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': 'No JSON data provided'}), 400

    target_value = data.get('target_value') or data.get('url') or data.get('curl') or ''
    target_type = data.get('target_type', 'url')
    param_name = data.get('param_name', 'query')
    step = data.get('step', 1)

    if not target_value:
        return jsonify({'code': 1, 'message': 'Target URL required'}), 400

    # 生成任务 ID
    task_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # 判断输入类型
    input_type = 'curl' if target_value.strip().lower().startswith('curl ') else 'url'

    # 简单提取 URL
    url = target_value
    if input_type == 'curl':
        url_match = re.search(r"'([^']+)'", target_value)
        if url_match:
            url = url_match.group(1)

    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'status': 'queued',
            'url': url,
            'input_type': input_type,
            'param_name': param_name
        }
    })


# Vercel 入口
handler = app