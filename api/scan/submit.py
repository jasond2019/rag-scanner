"""
API 入口 - 提交扫描任务
Vercel 文件路径: api/scan/submit.py → URL: /api/scan/submit
"""

from flask import Flask, request, jsonify
import asyncio
import uuid
import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner.format_detector import APIFormatDetector

app = Flask(__name__)


@app.route('/', methods=['POST', 'OPTIONS'])
def submit_scan():
    """提交扫描任务"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': 'Request body required'}), 400

    target_value = data.get('target_value') or data.get('url') or data.get('curl') or ''
    target_type = data.get('target_type', '')
    param_name_override = data.get('param_name')
    auth_token = data.get('auth_token')

    if not target_value:
        return jsonify({'code': 1, 'message': 'Target URL required'}), 400

    # 自动识别输入类型
    if not target_type:
        if target_value.strip().lower().startswith('curl '):
            target_type = 'curl'
        else:
            target_type = 'url'

    # 处理 curl 命令
    curl_data = None
    format_info = None

    if target_type == 'curl' or target_value.strip().lower().startswith('curl '):
        try:
            format_detector = APIFormatDetector()

            def detect_sync():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(format_detector._detect_from_curl(target_value))
                finally:
                    loop.close()

            curl_data = detect_sync()

            if param_name_override:
                curl_data['param_name'] = param_name_override

            format_info = {
                'input_type': 'curl',
                'param_name': curl_data.get('param_name'),
                'method': curl_data.get('method'),
                'confidence': 1.0,
            }
            target_type = 'url'

        except Exception as e:
            return jsonify({'code': 1, 'message': f'curl parse failed: {str(e)}'}), 400
    else:
        format_info = {
            'input_type': 'url',
            'param_name': param_name_override or 'query',
            'method': 'POST',
            'confidence': 0.5,
        }

        if auth_token:
            curl_data = {
                'url': target_value,
                'method': 'POST',
                'param_name': param_name_override or 'query',
                'headers': {'Authorization': auth_token, 'Content-Type': 'application/json'},
                'extra_params': {}
            }

    # 生成任务 ID
    task_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # 返回结果（简化版，不依赖数据库）
    result = {
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'status': 'queued',
            'estimated_time': 60,
            'step': 1,
            'format_detected': format_info,
            'url': curl_data.get('url', target_value) if curl_data else target_value
        }
    }

    return jsonify(result)


# Vercel 入口
handler = app