"""
Admin Task Detail API
GET /api/admin/detail - 获取任务详细信息（包含漏洞详情）
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


# 检测器名称映射
DETECTOR_NAMES = {
    "RAG-SEC-001": "Prompt Injection",
    "RAG-SEC-002": "Jailbreak",
    "RAG-SEC-003": "Privacy Leak",
    "RAG-SEC-004": "Sensitive Data",
    "RAG-SEC-005": "Auth Bypass",
    "RAG-SEC-006": "Data Leak",
    "RAG-SEC-007": "Model Manipulation",
    "RAG-SEC-008": "Context Poisoning",
    "RAG-SEC-009": "Query Manipulation",
    "RAG-SEC-010": "Response Manipulation",
}


@app.route('/api/admin/detail', methods=['GET', 'POST'])
def get_task_detail():
    """获取任务详细信息"""
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
                'suggestion': vuln.suggestion,
                'evidence': vuln.evidence[:200] if vuln.evidence else None,
            })

        # 构建详情
        detail = {
            'task': {
                'id': task.id,
                'target_type': task.target_type,
                'target_value': task.target_value,
                'status': task.status,
                'progress': task.progress,
                'current_step': task.current_step,
                'score': task.score,
                'level': task.level,
                'created_at': task.created_at.isoformat() if task.created_at else None,
            },
            'vulnerabilities': vulnerabilities,
            'detector_summary': detector_vulns,
            'total_vulnerabilities': len(vulnerabilities),
            'critical_count': sum(1 for v in vulnerabilities if v.severity == 'critical'),
            'high_count': sum(1 for v in vulnerabilities if v.severity == 'high'),
            'medium_count': sum(1 for v in vulnerabilities if v.severity == 'medium'),
            'low_count': sum(1 for v in vulnerabilities if v.severity == 'low'),
        }

        return jsonify({
            'success': True,
            'data': detail
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