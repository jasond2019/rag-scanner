"""
测试 API - 验证 Vercel Python 是否工作
"""

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 启用 CORS


@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({
        'message': 'Hello from Vercel Python!',
        'status': 'ok'
    })


@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'message': 'Root endpoint',
        'available': ['/api/hello']
    })


# Vercel 入口
handler = app