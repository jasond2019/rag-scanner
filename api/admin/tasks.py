"""
Admin Tasks List API
GET /api/admin/tasks - 获取最近扫描任务列表
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


@app.route('/api/admin/tasks', methods=['GET', 'POST'])
def get_tasks():
    """获取最近扫描任务列表"""
    db = get_session()
    if not db:
        return jsonify({
            'error': 'Database not available',
            'details': db_error
        }), 503

    try:
        # 获取分页参数
        limit = request.args.get('limit', default=20, type=int)
        offset = request.args.get('offset', default=0, type=int)
        status_filter = request.args.get('status', default=None, type=str)

        # 构建查询
        query = db.query(ScanTask)

        # 状态过滤
        if status_filter:
            query = query.filter_by(status=status_filter)

        # 按创建时间倒序
        query = query.order_by(ScanTask.created_at.desc())

        # 分页
        tasks = query.limit(limit).offset(offset).all()

        # 总数
        total_query = db.query(ScanTask)
        if status_filter:
            total_query = total_query.filter_by(status=status_filter)
        total = total_query.count()

        # 格式化输出
        task_list = []
        for task in tasks:
            task_list.append({
                'id': task.id,
                'target_type': task.target_type,
                'target_value': task.target_value,
                'status': task.status,
                'progress': task.progress,
                'current_step': task.current_step,
                'score': task.score,
                'level': task.level,
                'created_at': task.created_at.isoformat() if task.created_at else None,
            })

        return jsonify({
            'success': True,
            'data': {
                'tasks': task_list,
                'total': total,
                'limit': limit,
                'offset': offset
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