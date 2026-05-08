"""
Report Download API
GET /api/report/download - 下载扫描报告（JSON文件）
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
import sys
import os
from datetime import datetime

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, api_dir)

from lib.db import get_session, ScanTask, Vulnerability, db_error

app = Flask(__name__)
CORS(app)


@app.route('/api/report/download', methods=['GET', 'POST'])
def download_report():
    """下载扫描报告（JSON文件）"""
    db = get_session()
    if not db:
        return jsonify({
            'error': 'Database not available',
            'details': db_error
        }), 503

    try:
        # 获取任务ID参数
        task_id = request.args.get('task_id', default=None, type=str)

        if not task_id:
            return jsonify({
                'success': False,
                'error': 'task_id parameter is required'
            }), 400

        # 查询任务
        task = db.query(ScanTask).filter_by(id=task_id).first()
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404

        # 查询漏洞
        vulnerabilities = db.query(Vulnerability).filter_by(
            task_id=task_id
        ).all()

        # 构建报告
        report = {
            'report_id': f"RPT-{task_id}",
            'generated_at': datetime.utcnow().isoformat(),
            'task': {
                'id': task.id,
                'target_type': task.target_type,
                'target_value': task.target_value,
                'status': task.status,
                'score': task.score,
                'level': task.level,
                'created_at': task.created_at.isoformat() if task.created_at else None,
            },
            'summary': {
                'total_vulnerabilities': len(vulnerabilities),
                'critical_count': sum(1 for v in vulnerabilities if v.severity == 'critical'),
                'high_count': sum(1 for v in vulnerabilities if v.severity == 'high'),
                'medium_count': sum(1 for v in vulnerabilities if v.severity == 'medium'),
                'low_count': sum(1 for v in vulnerabilities if v.severity == 'low'),
                'score': task.score,
                'risk_level': task.level,
            },
            'vulnerabilities': [
                {
                    'id': v.id,
                    'rule_id': v.rule_id,
                    'name': v.name,
                    'severity': v.severity,
                    'score_deduction': v.score_deduction,
                    'description': v.description,
                    'suggestion': v.suggestion,
                    'evidence': v.evidence,
                }
                for v in vulnerabilities
            ],
        }

        # 生成 JSON 文件响应
        json_content = json.dumps(report, indent=2, ensure_ascii=False)
        filename = f"scan-report-{task_id}.json"

        return Response(
            json_content,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/json; charset=utf-8',
            }
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db.close()


# Vercel 入口
handler = app