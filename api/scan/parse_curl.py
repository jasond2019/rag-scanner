"""
API 入口 - 解析 curl 命令
Vercel 文件路径: api/scan/parse_curl.py → URL: /api/scan/parse_curl
"""

from flask import Flask, request, jsonify
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner.format_detector import APIFormatDetector

app = Flask(__name__)


@app.route('/', methods=['POST', 'OPTIONS'])
def parse_curl():
    """解析 curl 命令"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    data = request.get_json()
    curl_cmd = data.get('curl', '')

    if not curl_cmd:
        return jsonify({'code': 1, 'message': 'curl command cannot be empty'}), 400

    if not curl_cmd.strip().lower().startswith('curl '):
        return jsonify({'code': 1, 'message': 'Invalid curl command'}), 400

    try:
        format_detector = APIFormatDetector()

        def parse_sync():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(format_detector._detect_from_curl(curl_cmd))
            finally:
                loop.close()

        parsed = parse_sync()

        # 提取认证信息
        auth_header = None
        headers = parsed.get('headers', {})
        for key in ['Authorization', 'X-API-Key', 'Api-Key', 'Bearer', 'Token']:
            if key in headers:
                auth_header = f"{key}: {headers[key][:20]}..." if len(headers[key]) > 20 else f"{key}: {headers[key]}"
                break

        if 'Authorization' in headers:
            auth_value = headers['Authorization']
            if auth_value.startswith('Bearer '):
                token_preview = auth_value[7:27] + '...' if len(auth_value) > 27 else auth_value[7:]
                auth_header = f"Bearer {token_preview}"

        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'url': parsed.get('url', ''),
                'method': parsed.get('method', 'POST'),
                'param_name': parsed.get('param_name', 'query'),
                'auth_header': auth_header,
                'has_body': parsed.get('body') is not None,
                'headers': headers,
                'extra_params': parsed.get('extra_params', {})
            }
        })

    except Exception as e:
        return jsonify({'code': 1, 'message': f'curl parse failed: {str(e)}'}), 400


# Vercel 入口
handler = app