"""
API 入口 - 获取扫描结果
Vercel 文件路径: api/scan/[task_id]/result.py → URL: /api/scan/{task_id}/result
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/', methods=['GET', 'OPTIONS'])
def get_scan_result():
    """获取扫描结果"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    # 从查询参数获取 task_id
    task_id = request.args.get('task_id') or request.path.split('/')[-2]

    if not task_id:
        return jsonify({'code': 1, 'message': 'task_id required'}), 400

    # 模拟结果响应（简化版）
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'step': 1,
            'is_final': True,
            'score': 85,
            'level': 'medium',
            'vulnerabilities': [],
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