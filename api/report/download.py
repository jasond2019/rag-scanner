"""
Report API
合并 Generate 和 Download 端点到一个 Serverless Function
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


def _generate_recommendations(vulnerabilities):
    """根据漏洞生成修复建议"""
    recommendations = []
    vuln_types = set()
    for v in vulnerabilities:
        if v.rule_id:
            vuln_types.add(v.rule_id[:10])

    if 'RAG-SEC-001' in vuln_types:
        recommendations.append({
            'type': 'Prompt Injection',
            'priority': 'high',
            'description': '检测到提示注入漏洞',
            'actions': ['添加输入长度限制', '实施特殊字符过滤', '使用提示模板']
        })
    if 'RAG-SEC-002' in vuln_types:
        recommendations.append({
            'type': 'Jailbreak',
            'priority': 'high',
            'description': '检测到越狱攻击尝试',
            'actions': ['强化系统提示边界', '添加角色扮演检测']
        })
    if 'RAG-SEC-003' in vuln_types or 'RAG-SEC-004' in vuln_types:
        recommendations.append({
            'type': 'Privacy/Sensitive',
            'priority': 'medium',
            'description': '检测到隐私或敏感数据泄露风险',
            'actions': ['审查数据源权限', '添加敏感词过滤']
        })
    return recommendations


def _build_report(task, vulnerabilities):
    """构建报告数据"""
    return {
        'report_id': f"RPT-{task.id}",
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
        'recommendations': _generate_recommendations(vulnerabilities),
    }


# ============ Generate API (返回 JSON) ============
@app.route('/api/report/generate', methods=['GET', 'POST', 'OPTIONS'])
def generate_report():
    """生成扫描报告（JSON格式，返回在响应体中）"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    db = get_session()
    if not db:
        return jsonify({'code': 1, 'message': 'Database not available', 'details': db_error}), 503

    try:
        task_id = request.args.get('task_id', default=None, type=str)
        if not task_id and request.is_json:
            data = request.get_json()
            task_id = data.get('task_id')

        if not task_id:
            return jsonify({'code': 1, 'message': 'task_id parameter required'}), 400

        task = db.query(ScanTask).filter_by(id=task_id).first()
        if not task:
            return jsonify({'code': 1, 'message': 'Task not found'}), 404

        vulnerabilities = db.query(Vulnerability).filter_by(task_id=task_id).all()
        report = _build_report(task, vulnerabilities)

        return jsonify({'code': 0, 'message': 'success', 'data': report})
    except Exception as e:
        return jsonify({'code': 1, 'message': str(e)}), 500
    finally:
        db.close()


# ============ Download API (返回文件) ============
@app.route('/api/report/download', methods=['GET', 'POST', 'OPTIONS'])
def download_report():
    """下载扫描报告（JSON文件）"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    db = get_session()
    if not db:
        return jsonify({'error': 'Database not available', 'details': db_error}), 503

    try:
        task_id = request.args.get('task_id', default=None, type=str)
        if not task_id:
            return jsonify({'success': False, 'error': 'task_id parameter is required'}), 400

        task = db.query(ScanTask).filter_by(id=task_id).first()
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404

        vulnerabilities = db.query(Vulnerability).filter_by(task_id=task_id).all()
        report = _build_report(task, vulnerabilities)

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
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# Vercel 入口
handler = app