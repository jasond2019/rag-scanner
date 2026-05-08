"""
API 入口 - 提交扫描任务
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import re
import sys
import os
from datetime import datetime

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, api_dir)

app = Flask(__name__)
CORS(app)


@app.route('/api/scan/submit', methods=['POST', 'GET', 'OPTIONS'])
def submit_scan():
    """提交扫描任务"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    if request.method == 'GET':
        try:
            from lib.db import get_db_status
            db_status = get_db_status()
        except Exception as e:
            db_status = {'error': str(e)}
        return jsonify({
            'code': 0,
            'message': 'submit API is running',
            'usage': 'POST with {"target_value": "curl or URL"}',
            'db_status': db_status
        })

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': 'No JSON data provided'}), 400

    target_value = data.get('target_value') or data.get('url') or data.get('curl') or ''
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

    # 保存到数据库
    try:
        from lib.db import get_session, init_db, get_db_status, ScanTask
        db_status = get_db_status()
        init_db()
        db = get_session()
        if db:
            task = ScanTask(
                id=task_id,
                target_type=input_type,
                target_value=target_value,
                status='queued',
                progress=0,
                current_step='waiting'
            )
            db.add(task)
            db.commit()
            db.close()
            db_status['saved'] = True
        else:
            db_status['saved'] = False
    except Exception as e:
        db_status = {'save_error': str(e), 'saved': False}

    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'status': 'queued',
            'url': url,
            'input_type': input_type,
            'param_name': param_name,
            'db_status': db_status
        }
    })


# Vercel 入口
handler = app