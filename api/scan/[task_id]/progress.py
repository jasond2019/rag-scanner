"""
API 入口 - 获取扫描进度
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route('/api/scan/<task_id>/progress', methods=['GET', 'OPTIONS'])
def get_scan_progress(task_id):
    """获取扫描进度"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    if not task_id:
        return jsonify({'code': 1, 'message': 'task_id required'}), 400

    # 模拟进度响应
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'status': 'completed',
            'progress': 100,
            'current_step': 'finished',
            'step': 1,
            'score': 85
        }
    })


# Vercel 入口
handler = app