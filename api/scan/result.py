"""
API 入口 - 获取扫描结果（查询参数方式）
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route('/api/scan/result', methods=['GET', 'OPTIONS'])
def get_scan_result():
    """获取扫描结果"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'code': 1, 'message': 'task_id parameter required'}), 400

    # 返回模拟扫描结果
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'step': 1,
            'is_final': True,
            'score': 85,
            'level': 'medium',
            'vulnerabilities': [
                {
                    'id': 'vuln_001',
                    'name': 'Prompt Injection Risk',
                    'severity': 'medium',
                    'description': 'API may be vulnerable to prompt injection attacks',
                    'suggestion': 'Add input validation and sanitization'
                },
                {
                    'id': 'vuln_002',
                    'name': 'Missing Rate Limiting',
                    'severity': 'low',
                    'description': 'No rate limiting detected on API endpoint',
                    'suggestion': 'Implement rate limiting to prevent abuse'
                }
            ],
            'score_breakdown': {
                'base_score': 100,
                'total_deduction': 15,
                'final_score': 85
            },
            'report_url': f'/api/report/generate?task_id={task_id}'
        }
    })


# Vercel 入口
handler = app