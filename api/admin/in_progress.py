"""
Admin In-Progress Tasks API
GET /api/admin/in_progress - 获取正在进行中的扫描任务
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, api_dir)

from lib.db import get_session, ScanTask, db_error

app = Flask(__name__)
CORS(app)


@app.route('/api/admin/in_progress', methods=['GET', 'POST'])
def get_in_progress_tasks():
    """获取正在进行中的扫描任务"""
    db = get_session()
    if not db:
        return jsonify({
            'error': 'Database not available',
            'details': db_error
        }), 503

    try:
        # 查询进行中的任务（queued, running, scanning）
        tasks = db.query(ScanTask).filter(
            ScanTask.status.in_(['queued', 'running', 'scanning'])
        ).order_by(ScanTask.created_at.desc()).all()

        # 格式化输出
        in_progress_list = []
        for task in tasks:
            in_progress_list.append({
                'id': task.id,
                'target_type': task.target_type,
                'target_value': task.target_value,
                'status': task.status,
                'progress': task.progress,
                'current_step': task.current_step,
                'created_at': task.created_at.isoformat() if task.created_at else None,
            })

        return jsonify({
            'success': True,
            'data': {
                'tasks': in_progress_list,
                'total': len(in_progress_list)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


# Vercel 入口
handler = app