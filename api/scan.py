"""
API 入口 - 扫描相关接口合并版
包含: submit, parse_curl, progress, execute, result, health
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import uuid
import json
import re
import traceback
from datetime import datetime

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, api_dir)

app = Flask(__name__)
CORS(app)


# ==================== 检测器列表 ====================
DETECTORS = [
    {"name": "提示词注入检测", "key": "prompt_injection"},
    {"name": "越狱攻击检测", "key": "jailbreak"},
    {"name": "数据泄露检测", "key": "data_leak"},
    {"name": "权限绕过检测", "key": "auth_bypass"},
    {"name": "隐私数据检测", "key": "privacy"},
    {"name": "敏感内容检测", "key": "sensitive"},
]


# ==================== 健康检查 ====================
@app.route('/api/scan', methods=['GET', 'OPTIONS'])
@app.route('/api/hello', methods=['GET', 'OPTIONS'])
def health_check():
    """健康检查"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    try:
        from lib.db import get_db_status, init_db, engine
        init_db()
        db_status = get_db_status()
    except Exception as e:
        db_status = {'error': str(e)}

    return jsonify({
        'code': 0,
        'message': 'RAG Scanner API is running',
        'endpoints': ['submit', 'parse_curl', 'progress', 'execute', 'result'],
        'db_status': db_status
    })


# ==================== 解析 curl ====================
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
        return jsonify({'code': 1, 'message': 'Invalid curl command'}), 400

    try:
        parsed = parse_curl_simple(curl_cmd)
        return jsonify({'code': 0, 'message': 'success', 'data': parsed})
    except Exception as e:
        return jsonify({'code': 1, 'message': f'Parse failed: {str(e)}'}), 400


# ==================== 提交任务 ====================
@app.route('/api/scan/submit', methods=['POST', 'GET', 'OPTIONS'])
def submit_scan():
    """提交扫描任务"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    if request.method == 'GET':
        try:
            from lib.db import get_db_status
            db_status = get_db_status()
        except:
            db_status = {}
        return jsonify({
            'code': 0,
            'message': 'submit API is running',
            'usage': 'POST with {"target_value": "curl or URL"}',
            'db_status': db_status
        })

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': 'No JSON data provided'}), 400

    target_value = data.get('target_value') or data.get('url') or data.get('curl') or ''
    param_name = data.get('param_name', 'query')
    user_id = data.get('user_id') or request.headers.get('X-User-ID') or 'anonymous'  # 获取用户 ID

    if not target_value:
        return jsonify({'code': 1, 'message': 'Target URL required'}), 400

    # 生成任务 ID
    task_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # 判断输入类型
    input_type = 'curl' if target_value.strip().lower().startswith('curl ') else 'url'

    # 提取 URL
    url = target_value
    if input_type == 'curl':
        url_match = re.search(r"'([^']+)'", target_value)
        if url_match:
            url = url_match.group(1)

    # 保存到数据库
    db_saved = False
    try:
        from lib.db import get_session, init_db, ScanTask
        init_db()
        db = get_session()
        if db:
            task = ScanTask(
                id=task_id,
                target_type=input_type,
                target_value=target_value,
                status='queued',
                progress=0,
                current_step='waiting',
                user_id=user_id  # 保存用户 ID
            )
            db.add(task)
            db.commit()
            db.close()
            db_saved = True
    except Exception as e:
        print(f"DB save error: {e}")

    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'task_id': task_id,
            'status': 'queued',
            'url': url,
            'input_type': input_type,
            'param_name': param_name,
            'db_saved': db_saved
        }
    })


# ==================== 查询进度 ====================
@app.route('/api/scan/progress', methods=['GET', 'OPTIONS'])
def get_scan_progress():
    """查询扫描进度"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'code': 1, 'message': 'task_id required'}), 400

    try:
        from lib.db import get_session, init_db, ScanTask, Vulnerability

        init_db()
        db = get_session()

        if not db:
            return jsonify({'code': 1, 'message': 'Database connection failed'}), 500

        task = db.query(ScanTask).filter(ScanTask.id == task_id).first()

        if not task:
            db.close()
            return jsonify({'code': 1, 'message': f'Task not found: {task_id}'}), 404

        response_data = {
            'task_id': task_id,
            'status': task.status or 'queued',
            'progress': task.progress or 0,
            'current_step': task.current_step or 'waiting',
        }

        # 完成状态返回结果
        if task.status == 'completed':
            response_data['score'] = task.score
            response_data['level'] = task.level
            vuln_count = db.query(Vulnerability).filter(
                Vulnerability.task_id == task_id
            ).count()
            response_data['vulnerabilities_count'] = vuln_count

        # 失败状态
        if task.status == 'failed':
            response_data['error'] = '扫描失败'

        db.close()
        return jsonify({'code': 0, 'message': 'success', 'data': response_data})

    except Exception as e:
        return jsonify({'code': 1, 'message': f'Query failed: {str(e)}'}), 500


# ==================== 执行扫描 ====================
@app.route('/api/scan/execute', methods=['POST', 'GET', 'OPTIONS'])
def execute_scan():
    """执行扫描任务"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    if request.method == 'GET':
        return jsonify({
            'code': 0,
            'message': 'execute API is running',
            'detectors': [d['name'] for d in DETECTORS]
        })

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': 'No JSON data provided'}), 400

    task_id = data.get('task_id')
    url = data.get('url')
    headers = data.get('headers', {})
    param_name = data.get('param_name', 'query')

    if not task_id or not url:
        return jsonify({'code': 1, 'message': 'task_id and url required'}), 400

    try:
        from scanner.engine import ScanEngine
        from lib.db import get_session, ScanTask, Vulnerability, init_db

        init_db()
        db = get_session()

        if not db:
            return jsonify({'code': 1, 'message': 'Database connection failed'}), 500

        # 步骤 1: 初始化
        task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
        if not task:
            db.close()
            return jsonify({'code': 1, 'message': 'Task not found'}), 404

        task.status = 'running'
        task.progress = 5
        task.current_step = '初始化扫描引擎'
        db.commit()

        # 步骤 2: 加载规则
        task.progress = 20
        task.current_step = '加载检测规则'
        db.commit()

        engine = ScanEngine()

        # 步骤 3: 执行检测器
        all_vulnerabilities = []
        progress_per_detector = 60 / len(DETECTORS)

        for i, detector_info in enumerate(DETECTORS):
            detector_name = detector_info['name']
            task.current_step = detector_name
            task.progress = 20 + int(i * progress_per_detector)
            db.commit()

            try:
                engine.detectors[detector_info['key']].set_request_format({
                    "method": "POST",
                    "param_name": param_name,
                    "headers": headers,
                })
                vulns = engine.detectors[detector_info['key']].detect(url, headers, task_id)
                if vulns:
                    all_vulnerabilities.extend(vulns)
            except Exception as e:
                print(f"Detector {detector_name} failed: {e}")

            task.progress = 20 + int((i + 1) * progress_per_detector)
            db.commit()

        # 步骤 4: 计算评分（使用 VulnerabilityScorer 直接计算）
        task.current_step = '计算安全评分'
        task.progress = 80
        db.commit()

        from scanner.scorer import VulnerabilityScorer
        scorer = VulnerabilityScorer()
        score_breakdown = scorer.calculate_breakdown(all_vulnerabilities)
        final_score = score_breakdown["final_score"]
        risk_level = scorer.get_risk_level(final_score)

        # 步骤 5: 保存漏洞
        task.current_step = '保存检测结果'
        task.progress = 90
        db.commit()

        for i, vuln in enumerate(all_vulnerabilities):
            vuln_id = f"{task_id}_{vuln.get('rule_id', 'unknown')}_{i}_{uuid.uuid4().hex[:4]}"
            vuln_record = Vulnerability(
                id=vuln_id,
                task_id=task_id,
                rule_id=vuln.get('rule_id', ''),
                name=vuln.get('name', ''),
                severity=vuln.get('severity', 'medium'),
                score_deduction=vuln.get('score_deduction', 0),
                description=vuln.get('description', ''),
                suggestion=vuln.get('suggestion', ''),
                evidence=json.dumps(vuln.get('evidence', [])),
            )
            db.add(vuln_record)

        db.commit()

        # 步骤 6: 完成
        task.status = 'completed'
        task.progress = 100
        task.current_step = '扫描完成'
        task.score = final_score
        task.level = risk_level
        task.completed_at = datetime.utcnow()
        db.commit()
        db.close()

        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'task_id': task_id,
                'score': final_score,
                'level': risk_level,
                'vulnerabilities': all_vulnerabilities,
                'score_breakdown': score_breakdown,
            }
        })

    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"Execute scan error: {error_detail}")

        try:
            task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
            if task:
                task.status = 'failed'
                task.progress = 0
                task.current_step = '扫描失败'
                db.commit()
        except:
            pass

        db.close()
        return jsonify({
            'code': 1,
            'message': f'扫描执行失败: {str(e)}',
            'data': {'task_id': task_id, 'status': 'failed', 'error': str(e)}
        }), 500


# ==================== 查询结果 ====================
@app.route('/api/scan/result', methods=['GET', 'OPTIONS'])
def get_scan_result():
    """获取扫描结果"""
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'code': 1, 'message': 'task_id required'}), 400

    try:
        from lib.db import get_session, ScanTask, Vulnerability

        db = get_session()
        if not db:
            return jsonify({'code': 1, 'message': 'Database connection failed'}), 500

        task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
        vulns = db.query(Vulnerability).filter(Vulnerability.task_id == task_id).all()

        if task:
            vuln_list = []
            for v in vulns:
                evidence_data = []
                if v.evidence:
                    try:
                        evidence_data = json.loads(v.evidence)
                    except:
                        evidence_data = [v.evidence]

                vuln_list.append({
                    'id': v.id,
                    'rule_id': v.rule_id,
                    'name': v.name,
                    'severity': v.severity,
                    'score_deduction': v.score_deduction,
                    'description': v.description,
                    'suggestion': v.suggestion,
                    'evidence': evidence_data,
                })

            score = task.score if task.score is not None else 100
            level = task.level if task.level is not None else 'low'

            db.close()

            return jsonify({
                'code': 0,
                'message': 'success',
                'data': {
                    'task_id': task_id,
                    'score': score,
                    'level': level,
                    'vulnerabilities': vuln_list,
                    'status': task.status,
                    'report_url': f'/api/report?action=generate&task_id={task_id}'
                }
            })

        db.close()
        return jsonify({'code': 1, 'message': 'Task not found'}), 404

    except Exception as e:
        return jsonify({'code': 1, 'message': f'Query failed: {str(e)}'}), 500


# Vercel 入口
handler = app