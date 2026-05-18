"""
Report API - 合并版
包含: generate, download
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
import sys
import os
from datetime import datetime

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, api_dir)

from lib.db import get_session, ScanTask, Vulnerability, db_error

app = Flask(__name__)
CORS(app)


# 扫描维度定义
SCAN_DIMENSIONS = [
    {'id': 'RAG-SEC-001', 'name': 'Prompt Injection', 'rules_count': 286},
    {'id': 'RAG-SEC-002', 'name': 'Privacy Leak', 'rules_count': 14},
    {'id': 'RAG-SEC-005', 'name': 'Auth Bypass', 'rules_count': 10},
    {'id': 'RAG-SEC-007', 'name': 'Sensitive Data', 'rules_count': 518},
    {'id': 'RAG-SEC-008', 'name': 'Jailbreak', 'rules_count': 120},
    {'id': 'RAG-SEC-006', 'name': 'Data Leak', 'rules_count': 15},
]


def _get_dimension_results(vulnerabilities):
    """获取每个维度的检测结果"""
    dimension_results = []
    vuln_by_dimension = {}

    for v in vulnerabilities:
        dim_id = v.rule_id[:10] if v.rule_id else 'Unknown'
        if dim_id not in vuln_by_dimension:
            vuln_by_dimension[dim_id] = []
        vuln_by_dimension[dim_id].append(v)

    for dim in SCAN_DIMENSIONS:
        dim_vulns = vuln_by_dimension.get(dim['id'], [])
        dimension_results.append({
            'id': dim['id'],
            'name': dim['name'],
            'vulnerabilities_found': len(dim_vulns),
            'score_impact': sum(v.score_deduction for v in dim_vulns),
        })

    return dimension_results


def _build_report(task, vulnerabilities):
    """构建报告数据"""
    dimension_results = _get_dimension_results(vulnerabilities)

    return {
        'report_id': f"RPT-{task.id}",
        'generated_at': datetime.utcnow().isoformat(),
        'task': {
            'id': task.id,
            'target_value': task.target_value,
            'score': task.score,
            'level': task.level,
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
        'dimensions': dimension_results,
        'vulnerabilities': [
            {'id': v.id, 'name': v.name, 'severity': v.severity, 'description': v.description}
            for v in vulnerabilities
        ],
    }


# ==================== Generate API ====================
@app.route('/api/report', methods=['GET', 'OPTIONS'])
@app.route('/api/report/generate', methods=['GET', 'POST', 'OPTIONS'])
def generate_report():
    """生成扫描报告"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    db = get_session()
    if not db:
        return jsonify({'code': 1, 'message': 'Database not available'}), 503

    try:
        task_id = request.args.get('task_id')
        if not task_id:
            return jsonify({'code': 1, 'message': 'task_id required'}), 400

        task = db.query(ScanTask).filter_by(id=task_id).first()
        if not task:
            db.close()
            return jsonify({'code': 1, 'message': 'Task not found'}), 404

        vulnerabilities = db.query(Vulnerability).filter_by(task_id=task_id).all()
        report = _build_report(task, vulnerabilities)

        db.close()
        return jsonify({'code': 0, 'message': 'success', 'data': report})
    except Exception as e:
        db.close()
        return jsonify({'code': 1, 'message': str(e)}), 500


# ==================== Download API ====================
@app.route('/api/report/download', methods=['GET', 'OPTIONS'])
def download_report():
    """下载扫描报告"""
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
            db.close()
            return jsonify({'success': False, 'error': 'Task not found'}), 404

        vulnerabilities = db.query(Vulnerability).filter_by(task_id=task_id).all()
        report = _build_report(task, vulnerabilities)

        json_content = json.dumps(report, indent=2, ensure_ascii=False)
        filename = f"scan-report-{task_id}.json"

        db.close()
        return Response(
            json_content,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 500


# Vercel 入口
handler = app