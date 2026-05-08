"""
Admin User History API
GET /api/admin/history - 获取用户扫描历史
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


@app.route('/api/admin/history', methods=['GET', 'POST'])
def get_user_history():
    """获取用户扫描历史"""
    db = get_session()
    if not db:
        return jsonify({
            'error': 'Database not available',
            'details': db_error
        }), 503

    try:
        # 获取用户ID参数
        user_id = request.args.get('user_id', default=None, type=str)
        limit = request.args.get('limit', default=50, type=int)

        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id parameter is required'
            }), 400

        # 查询用户的扫描历史
        # 注意：当前 ScanTask 模型没有 user_id 字段
        # 如果需要支持，需要先更新数据库模型
        # 这里先返回所有任务作为临时方案
        tasks = db.query(ScanTask).order_by(
            ScanTask.created_at.desc()
        ).limit(limit).all()

        # 格式化输出
        history_list = []
        for task in tasks:
            history_list.append({
                'id': task.id,
                'target_type': task.target_type,
                'target_value': task.target_value,
                'status': task.status,
                'score': task.score,
                'level': task.level,
                'created_at': task.created_at.isoformat() if task.created_at else None,
            })

        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'history': history_list,
                'total': len(history_list)
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