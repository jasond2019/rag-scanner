"""
API 入口 - 生成 PDF 报告
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 启用 CORS


@app.route('/api/report/generate', methods=['GET', 'OPTIONS'])
def generate_report():
    """生成 PDF 报告"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'code': 1, 'message': 'task_id parameter required'}), 400

    # 模拟报告 URL（简化版）
    # 实际部署时可以使用 Vercel Blob 存储真实 PDF
    report_url = f'https://rag-scanner.vercel.app/reports/{task_id}.pdf'

    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'report_url': report_url,
            'download_url': report_url,
            'note': 'PDF generation requires Vercel Blob storage setup'
        }
    })


# Vercel 入口
handler = app