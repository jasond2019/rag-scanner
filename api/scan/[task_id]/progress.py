"""
API 入口 - 获取扫描进度
Vercel 文件路径: api/scan/[task_id]/progress.py → URL: /api/scan/{task_id}/progress
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/', methods=['GET', 'OPTIONS'])
def get_scan_progress():
    """获取扫描进度"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    # 从查询参数获取 task_id (Vercel 动态路由会自动注入)
    # 或者从 URL 路径中解析
    task_id = request.args.get('task_id') or request.path.split('/')[-2]

    if not task_id:
        return jsonify({'code': 1, 'message': 'task_id required'}), 400

    # 模拟进度响应（简化版，不依赖 KV）
    # 实际部署时可以连接 Vercel KV
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'status': 'queued',
            'progress': 0,
            'current_step': 'waiting',
            'step': 1,
            'score': None
        }
    })


# Vercel 入口
handler = app