"""
Admin API - 合并版
包含: stats, tasks, history, in_progress, detail, logs
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, api_dir)

from lib.db import get_session, ScanTask, Vulnerability, db_error
from sqlalchemy import func

app = Flask(__name__)
CORS(app)


# 检测器名称映射
DETECTOR_NAMES = {
    "RAG-SEC-001": "Prompt Injection",
    "RAG-SEC-002": "Jailbreak",
    "RAG-SEC-003": "Privacy Leak",
    "RAG-SEC-004": "Sensitive Data",
    "RAG-SEC-005": "Auth Bypass",
    "RAG-SEC-006": "Data Leak",
}


# ==================== Stats API ====================
@app.route('/api/admin/stats', methods=['GET', 'OPTIONS'])
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


# ==================== Tasks API ====================
@app.route('/api/admin/tasks', methods=['GET', 'OPTIONS'])
def get_tasks():
    """获取最近扫描任务列表"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    db = get_session()
    if not db:
        return jsonify({'error': 'Database not available'}), 503

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
            'user_id': task.user_id or 'anonymous',
            'target_type': task.target_type,
            'target_value': task.target_value,
            'status': task.status,
            'progress': task.progress,
            'current_step': task.current_step,
            'score': task.score,
            'level': task.level,
            'created_at': task.created_at.isoformat() if task.created_at else None,
        } for task in tasks]

        return jsonify({'success': True, 'data': {'tasks': task_list, 'total': total}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== History API ====================
@app.route('/api/admin/history', methods=['GET', 'OPTIONS'])
def get_user_history():
    """获取用户扫描历史"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    db = get_session()
    if not db:
        return jsonify({'error': 'Database not available'}), 503

    try:
        user_id = request.args.get('user_id', default=None, type=str)
        limit = request.args.get('limit', default=50, type=int)

        if not user_id:
            return jsonify({'success': False, 'error': 'user_id required'}), 400

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

        return jsonify({'success': True, 'data': {'tasks': task_list, 'total': len(task_list)}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== In Progress API ====================
@app.route('/api/admin/in_progress', methods=['GET', 'OPTIONS'])
def get_in_progress_tasks():
    """获取正在进行中的扫描任务"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    db = get_session()
    if not db:
        return jsonify({'error': 'Database not available'}), 503

    try:
        tasks = db.query(ScanTask).filter(
            ScanTask.status.in_(['queued', 'running', 'scanning'])
        ).order_by(ScanTask.created_at.desc()).all()

        in_progress_list = [{
            'id': task.id,
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


# ==================== Detail API ====================
@app.route('/api/admin/detail', methods=['GET', 'OPTIONS'])
def get_task_detail():
    """获取任务详细信息"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    db = get_session()
    if not db:
        return jsonify({'error': 'Database not available'}), 503

    try:
        task_id = request.args.get('task_id')
        if not task_id:
            return jsonify({'success': False, 'error': 'task_id required'}), 400

        task = db.query(ScanTask).filter_by(id=task_id).first()
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404

        vulnerabilities = db.query(Vulnerability).filter_by(task_id=task_id).all()

        # 按检测器分组漏洞
        detector_vulns = {}
        for vuln in vulnerabilities:
            detector_id = vuln.rule_id[:10] if vuln.rule_id else "Unknown"
            detector_name = DETECTOR_NAMES.get(detector_id, detector_id)
            if detector_name not in detector_vulns:
                detector_vulns[detector_name] = []
            detector_vulns[detector_name].append({
                'id': vuln.id,
                'rule_id': vuln.rule_id,
                'name': vuln.name,
                'severity': vuln.severity,
                'score_deduction': vuln.score_deduction,
                'description': vuln.description,
            })

        detail = {
            'task': {
                'id': task.id,
                'target_value': task.target_value,
                'status': task.status,
                'progress': task.progress,
                'score': task.score,
                'level': task.level,
            },
            'vulnerabilities': [{'id': v.id, 'name': v.name, 'severity': v.severity} for v in vulnerabilities],
            'detector_summary': detector_vulns,
            'total_vulnerabilities': len(vulnerabilities),
        }

        return jsonify({'success': True, 'data': detail})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ==================== Logs API ====================
@app.route('/api/admin/logs', methods=['GET', 'OPTIONS'])
def get_audit_logs():
    """获取审计日志"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    db = get_session()
    if not db:
        return jsonify({'error': 'Database not available'}), 503

    try:
        limit = request.args.get('limit', default=100, type=int)

        tasks = db.query(ScanTask).order_by(ScanTask.created_at.desc()).limit(limit).all()

        logs = []
        for task in tasks:
            logs.append({
                'type': 'task',
                'task_id': task.id,
                'target': task.target_value[:100] if task.target_value else '',
                'status': task.status,
                'score': task.score,
                'timestamp': task.created_at.isoformat() if task.created_at else None,
            })

        return jsonify({'success': True, 'data': {'logs': logs, 'total': len(logs)}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# Vercel 入口
handler = app