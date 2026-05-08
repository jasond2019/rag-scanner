"""
Admin Statistics API
GET /api/admin/stats - 获取扫描统计数据
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


@app.route('/api/admin/stats', methods=['GET', 'POST'])
def get_stats():
    """获取扫描统计数据"""
    db = get_session()
    if not db:
        return jsonify({
            'error': 'Database not available',
            'details': db_error
        }), 503

    try:
        # 总任务数
        total_tasks = db.query(ScanTask).count()

        # 已完成任务数
        completed_tasks = db.query(ScanTask).filter_by(status='completed').count()

        # 进行中任务数
        in_progress_tasks = db.query(ScanTask).filter(
            ScanTask.status.in_(['queued', 'running', 'scanning'])
        ).count()

        # 失败任务数
        failed_tasks = db.query(ScanTask).filter_by(status='failed').count()

        # 平均分数（只计算已完成的任务）
        from sqlalchemy import func
        avg_score_result = db.query(func.avg(ScanTask.score)).filter(
            ScanTask.status == 'completed',
            ScanTask.score.isnot(None)
        ).scalar()
        avg_score = round(avg_score_result, 1) if avg_score_result else 0

        # 风险等级分布
        low_count = db.query(ScanTask).filter(
            ScanTask.status == 'completed',
            ScanTask.level == 'low'
        ).count()
        medium_count = db.query(ScanTask).filter(
            ScanTask.status == 'completed',
            ScanTask.level == 'medium'
        ).count()
        high_count = db.query(ScanTask).filter(
            ScanTask.status == 'completed',
            ScanTask.level == 'high'
        ).count()
        critical_count = db.query(ScanTask).filter(
            ScanTask.status == 'completed',
            ScanTask.level == 'critical'
        ).count()

        return jsonify({
            'success': True,
            'data': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'in_progress_tasks': in_progress_tasks,
                'failed_tasks': failed_tasks,
                'avg_score': avg_score,
                'risk_distribution': {
                    'low': low_count,
                    'medium': medium_count,
                    'high': high_count,
                    'critical': critical_count
                }
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