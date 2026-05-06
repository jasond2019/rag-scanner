"""
API 入口 - 生成 PDF 报告
Vercel 文件路径: api/report/generate.py → URL: /api/report/generate
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/', methods=['GET', 'OPTIONS'])
def generate_report():
    """生成 PDF 报告"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'code': 1, 'message': 'task_id required'}), 400

    # 简化版报告 URL
    report_url = f'https://blob.vercel-storage.com/reports/{task_id}.pdf'

    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'report_url': report_url,
            'download_url': report_url
        }
    })


# Vercel 入口
handler = app