"""
测试 API - 验证 Vercel Python 是否工作
"""

from flask import Flask, jsonify

app = Flask(__name__)


@app.route('/', methods=['GET'])
def hello():
    return jsonify({
        'message': 'Hello from Vercel Python!',
        'status': 'ok'
    })


# Vercel 入口
handler = app