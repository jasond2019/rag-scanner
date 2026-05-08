"""
Admin Audit Logs API
GET /api/admin/logs - 获取审计日志（基于扫描记录）
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, api_dir)

from lib.db import get_session, ScanTask, Vulnerability, db_error

app = Flask(__name__)
CORS(app)


@app.route('/api/admin/logs', methods=['GET', 'POST'])
def get_audit_logs():
    """获取审计日志"""
    db = get_session()
    if not db:
        return jsonify({
            'error': 'Database not available',
            'details': db_error
        }), 503

    try:
        # 获取分页参数
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # 查询所有任务作为日志记录
        tasks = db.query(ScanTask).order_by(
            ScanTask.created_at.desc()
        ).limit(limit).offset(offset).all()

        # 构建日志记录
        logs = []
        for task in tasks:
            # 任务创建日志
            logs.append({
                'type': 'task_created',
                'task_id': task.id,
                'target': task.target_value[:100],
                'status': task.status,
                'timestamp': task.created_at.isoformat() if task.created_at else None,
            })

            # 任务完成日志
            if task.status == 'completed':
                logs.append({
                    'type': 'task_completed',
                    'task_id': task.id,
                    'score': task.score,
                    'level': task.level,
                    'vulnerability_count': db.query(Vulnerability).filter_by(
                        task_id=task.id
                    ).count(),
                    'timestamp': task.created_at.isoformat() if task.created_at else None,
                })

        return jsonify({
            'success': True,
            'data': {
                'logs': logs,
                'total': len(logs),
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