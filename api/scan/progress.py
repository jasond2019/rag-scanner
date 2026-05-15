"""
API 入口 - 查询扫描进度
移除 fallback 模拟数据，返回真实状态
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, api_dir)

app = Flask(__name__)
CORS(app)


@app.route('/api/scan/progress', methods=['GET', 'OPTIONS'])
def get_scan_progress():
    """
    查询扫描进度

    Query params:
        task_id: 任务 ID

    Response:
        {
            "code": 0,
            "data": {
                "task_id": "scan_xxx",
                "status": "running",
                "progress": 45,
                "current_step": "提示词注入检测",
                "score": null,
                "level": null
            }
        }
    """
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'code': 1, 'message': 'task_id required'}), 400

    # 从数据库查询
    from lib.db import get_session, init_db, ScanTask, Vulnerability

    init_db()
    db = get_session()

    if not db:
        return jsonify({'code': 1, 'message': 'Database connection failed'}), 500

    task = db.query(ScanTask).filter(ScanTask.id == task_id).first()

    if not task:
        db.close()
        return jsonify({'code': 1, 'message': f'Task not found: {task_id}'}), 404

    response_data = {
        'task_id': task_id,
        'status': task.status or 'queued',
        'progress': task.progress or 0,
        'current_step': task.current_step or 'waiting',
    }

    # 完成状态返回结果
    if task.status == 'completed':
        response_data['score'] = task.score
        response_data['level'] = task.level

        # 统计漏洞数量
        vuln_count = db.query(Vulnerability).filter(
            Vulnerability.task_id == task_id
        ).count()
        response_data['vulnerabilities_count'] = vuln_count

    # 失败状态
    if task.status == 'failed':
        response_data['error'] = '扫描失败'

    db.close()

    return jsonify({
        'code': 0,
        'message': 'success',
        'data': response_data
    })


# Vercel 入口
handler = app