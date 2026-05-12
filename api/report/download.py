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


# 扫描维度定义（与检测器 RULE_ID 对应）
SCAN_DIMENSIONS = [
    {
        'id': 'RAG-SEC-001',
        'name': 'Prompt Injection Detection',
        'description': '检测提示注入攻击，包括指令覆盖、角色扮演等',
        'rules_count': 286,
        'category': 'injection',
        'detector': 'PromptInjectionDetector'
    },
    {
        'id': 'RAG-SEC-002',
        'name': 'Privacy Data Leak Detection',
        'description': '检测隐私数据泄露，包括 IP 地址、邮箱、电话等',
        'rules_count': 14,
        'category': 'privacy',
        'detector': 'PrivacyDetector'
    },
    {
        'id': 'RAG-SEC-005',
        'name': 'Authentication Bypass Detection',
        'description': '检测认证绕过风险，未授权访问等',
        'rules_count': 10,
        'category': 'auth',
        'detector': 'AuthBypassDetector'
    },
    {
        'id': 'RAG-SEC-007',
        'name': 'Sensitive Data Detection',
        'description': '检测敏感数据泄露，包括 API Key、密码、密钥等',
        'rules_count': 518,
        'category': 'sensitive',
        'detector': 'SensitiveDetector'
    },
    {
        'id': 'RAG-SEC-008',
        'name': 'Jailbreak Attack Detection',
        'description': '检测越狱攻击，包括 DAN、角色扮演绕过等',
        'rules_count': 120,
        'category': 'jailbreak',
        'detector': 'JailbreakDetector'
    },
    {
        'id': 'RAG-SEC-006',
        'name': 'Data Leak Detection',
        'description': '检测数据泄露风险，包括响应过度暴露等',
        'rules_count': 15,
        'category': 'data_leak',
        'detector': 'DataLeakDetector'
    },
]


def _get_dimension_results(vulnerabilities):
    """获取每个维度的检测结果"""
    dimension_results = []

    # 统计每个维度的漏洞
    vuln_by_dimension = {}
    for v in vulnerabilities:
        dim_id = v.rule_id[:10] if v.rule_id else 'Unknown'
        if dim_id not in vuln_by_dimension:
            vuln_by_dimension[dim_id] = []
        vuln_by_dimension[dim_id].append(v)

    # 构建维度结果
    for dim in SCAN_DIMENSIONS:
        dim_id = dim['id']
        dim_vulns = vuln_by_dimension.get(dim_id, [])

        dimension_results.append({
            'id': dim_id,
            'name': dim['name'],
            'description': dim['description'],
            'rules_count': dim['rules_count'],
            'category': dim['category'],
            'tested': True,
            'vulnerabilities_found': len(dim_vulns),
            'severity_distribution': {
                'critical': sum(1 for v in dim_vulns if v.severity == 'critical'),
                'high': sum(1 for v in dim_vulns if v.severity == 'high'),
                'medium': sum(1 for v in dim_vulns if v.severity == 'medium'),
                'low': sum(1 for v in dim_vulns if v.severity == 'low'),
            },
            'score_impact': sum(v.score_deduction for v in dim_vulns),
        })

    return dimension_results


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
    dimension_results = _get_dimension_results(vulnerabilities)

    return {
        'report_id': f"RPT-{task.id}",
        'generated_at': datetime.utcnow().isoformat(),
        'scanner_version': '1.0.0',
        'rules_version': '1.0.0',
        'task': {
            'id': task.id,
            'target_type': task.target_type,
            'target_value': task.target_value,
            'status': task.status,
            'score': task.score,
            'level': task.level,
            'created_at': task.created_at.isoformat() if task.created_at else None,
        },
        'scan_config': {
            'dimensions': 6,
            'total_rules': 963,
            'scan_mode': 'quick',
        },
        'scan_dimensions': dimension_results,
        'summary': {
            'total_vulnerabilities': len(vulnerabilities),
            'critical_count': sum(1 for v in vulnerabilities if v.severity == 'critical'),
            'high_count': sum(1 for v in vulnerabilities if v.severity == 'high'),
            'medium_count': sum(1 for v in vulnerabilities if v.severity == 'medium'),
            'low_count': sum(1 for v in vulnerabilities if v.severity == 'low'),
            'score': task.score,
            'risk_level': task.level,
            'dimensions_passed': sum(1 for d in dimension_results if d['vulnerabilities_found'] == 0),
            'dimensions_failed': sum(1 for d in dimension_results if d['vulnerabilities_found'] > 0),
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