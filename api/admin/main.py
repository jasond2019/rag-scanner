"""
Admin Main API
合并多个 Admin 端点到一个 Serverless Function
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, api_dir)

from lib.db import get_session, ScanTask, Vulnerability, db_error
from sqlalchemy import func

app = Flask(__name__)
CORS(app)


# ============ Stats API ============
@app.route('/api/admin/stats', methods=['GET', 'POST', 'OPTIONS'])
def get_stats():
    """获取扫描统计数据"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    db = get_session()
    if not db:
        return jsonify({'error': 'Database not available', 'details': db_error}), 503

    try:
        total_tasks = db.query(ScanTask).count()
        completed_tasks = db.query(ScanTask).filter_by(status='completed').count()
        in_progress_tasks = db.query(ScanTask).filter(
            ScanTask.status.in_(['queued', 'running', 'scanning'])
        ).count()
        failed_tasks = db.query(ScanTask).filter_by(status='failed').count()

        avg_score_result = db.query(func.avg(ScanTask.score)).filter(
            ScanTask.status == 'completed',
            ScanTask.score.isnot(None)
        ).scalar()
        avg_score = round(avg_score_result, 1) if avg_score_result else 0

        risk_distribution = {
            'low': db.query(ScanTask).filter(ScanTask.status == 'completed', ScanTask.level == 'low').count(),
            'medium': db.query(ScanTask).filter(ScanTask.status == 'completed', ScanTask.level == 'medium').count(),
            'high': db.query(ScanTask).filter(ScanTask.status == 'completed', ScanTask.level == 'high').count(),
            'critical': db.query(ScanTask).filter(ScanTask.status == 'completed', ScanTask.level == 'critical').count(),
        }

        return jsonify({
            'success': True,
            'data': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'in_progress_tasks': in_progress_tasks,
                'failed_tasks': failed_tasks,
                'avg_score': avg_score,
                'risk_distribution': risk_distribution
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ============ Tasks API ============
@app.route('/api/admin/tasks', methods=['GET', 'POST', 'OPTIONS'])
def get_tasks():
    """获取最近扫描任务列表"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    db = get_session()
    if not db:
        return jsonify({'error': 'Database not available', 'details': db_error}), 503

    try:
        limit = request.args.get('limit', default=20, type=int)
        offset = request.args.get('offset', default=0, type=int)
        status_filter = request.args.get('status', default=None, type=str)

        query = db.query(ScanTask)
        if status_filter:
            query = query.filter_by(status=status_filter)
        query = query.order_by(ScanTask.created_at.desc())
        tasks = query.limit(limit).offset(offset).all()

        total_query = db.query(ScanTask)
        if status_filter:
            total_query = total_query.filter_by(status=status_filter)
        total = total_query.count()

        task_list = [{
            'id': task.id,
            'target_type': task.target_type,
            'target_value': task.target_value,
            'status': task.status,
            'progress': task.progress,
            'current_step': task.current_step,
            'score': task.score,
            'level': task.level,
            'created_at': task.created_at.isoformat() if task.created_at else None,
        } for task in tasks]

        return jsonify({'success': True, 'data': {'tasks': task_list, 'total': total, 'limit': limit, 'offset': offset}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ============ History API ============
@app.route('/api/admin/history', methods=['GET', 'POST', 'OPTIONS'])
def get_user_history():
    """获取用户扫描历史"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    db = get_session()
    if not db:
        return jsonify({'error': 'Database not available', 'details': db_error}), 503

    try:
        user_id = request.args.get('user_id', default=None, type=str)
        limit = request.args.get('limit', default=50, type=int)

        if not user_id:
            return jsonify({'success': False, 'error': 'user_id parameter required'}), 400

        tasks = db.query(ScanTask).filter_by(user_id=user_id).order_by(
            ScanTask.created_at.desc()
        ).limit(limit).all()

        task_list = [{
            'id': task.id,
            'target_value': task.target_value[:100],
            'status': task.status,
            'score': task.score,
            'level': task.level,
            'created_at': task.created_at.isoformat() if task.created_at else None,
        } for task in tasks]

        return jsonify({'success': True, 'data': {'tasks': task_list, 'total': len(task_list), 'user_id': user_id}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ============ In Progress API ============
@app.route('/api/admin/in_progress', methods=['GET', 'POST', 'OPTIONS'])
def get_in_progress_tasks():
    """获取正在进行中的扫描任务"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    db = get_session()
    if not db:
        return jsonify({'error': 'Database not available', 'details': db_error}), 503

    try:
        tasks = db.query(ScanTask).filter(
            ScanTask.status.in_(['queued', 'running', 'scanning'])
        ).order_by(ScanTask.created_at.desc()).all()

        in_progress_list = [{
            'id': task.id,
            'target_type': task.target_type,
            'target_value': task.target_value,
            'status': task.status,
            'progress': task.progress,
            'current_step': task.current_step,
            'created_at': task.created_at.isoformat() if task.created_at else None,
        } for task in tasks]

        return jsonify({'success': True, 'data': {'tasks': in_progress_list, 'total': len(in_progress_list)}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# Vercel 入口
handler = app