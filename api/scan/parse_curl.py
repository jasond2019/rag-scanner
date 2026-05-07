"""
API 入口 - 解析 curl 命令
"""

from flask import Flask, request, jsonify
import re

app = Flask(__name__)


def parse_curl_simple(curl_cmd):
    """简单解析 curl 命令"""
    result = {
        'url': '',
        'method': 'POST',
        'param_name': 'query',
        'headers': {},
        'auth_header': None
    }

    # 提取 URL
    url_match = re.search(r"'([^']+)'", curl_cmd)
    if url_match:
        result['url'] = url_match.group(1)

    # 提取 Authorization
    auth_match = re.search(r"-H\s+'Authorization:\s*([^']+)'", curl_cmd)
    if auth_match:
        auth_value = auth_match.group(1)
        result['headers']['Authorization'] = auth_value
        if auth_value.startswith('Bearer '):
            token_preview = auth_value[7:27] + '...' if len(auth_value) > 27 else auth_value[7:]
            result['auth_header'] = f"Bearer {token_preview}"

    return result


@app.route('/api/scan/parse_curl', methods=['POST', 'GET', 'OPTIONS'])
def parse_curl():
    """解析 curl 命令"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    if request.method == 'GET':
        return jsonify({
            'code': 0,
            'message': 'parse_curl API is running',
            'usage': 'POST with {"curl": "curl command"}'
        })

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': 'No JSON data provided'}), 400

    curl_cmd = data.get('curl', '')
    if not curl_cmd:
        return jsonify({'code': 1, 'message': 'curl command cannot be empty'}), 400

    if not curl_cmd.strip().lower().startswith('curl '):
        return jsonify({'code': 1, 'message': 'Invalid curl command, must start with "curl "'}), 400

    try:
        parsed = parse_curl_simple(curl_cmd)
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': parsed
        })
    except Exception as e:
        return jsonify({'code': 1, 'message': f'Parse failed: {str(e)}'}), 400


# Vercel 入口
handler = app