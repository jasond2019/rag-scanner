"""
API 入口 - 执行扫描任务（分步更新进度）
Vercel Serverless 兼容版本
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import uuid
import json
import traceback
from datetime import datetime

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, api_dir)

app = Flask(__name__)
CORS(app)


# 检测器列表（定义步骤）
DETECTORS = [
    {"name": "提示词注入检测", "key": "prompt_injection"},
    {"name": "越狱攻击检测", "key": "jailbreak"},
    {"name": "数据泄露检测", "key": "data_leak"},
    {"name": "权限绕过检测", "key": "auth_bypass"},
    {"name": "隐私数据检测", "key": "privacy"},
    {"name": "敏感内容检测", "key": "sensitive"},
]


@app.route('/api/scan/execute', methods=['POST', 'GET', 'OPTIONS'])
def execute_scan():
    """
    执行扫描任务（分步更新进度）

    Request:
        {
            "task_id": "scan_xxx",
            "url": "https://example.com/api",
            "headers": {"Authorization": "Bearer xxx"},
            "param_name": "query"
        }

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": "scan_xxx",
                "score": 85,
                "level": "medium",
                "vulnerabilities": [...]
            }
        }
    """
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

    # 导入依赖
    from scanner.engine import ScanEngine
    from lib.db import get_session, ScanTask, Vulnerability, init_db

    init_db()
    db = get_session()

    if not db:
        return jsonify({'code': 1, 'message': 'Database connection failed'}), 500

    try:
        # ===== 步骤 1: 初始化 (progress: 5%) =====
        task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
        if not task:
            db.close()
            return jsonify({'code': 1, 'message': 'Task not found'}), 404

        task.status = 'running'
        task.progress = 5
        task.current_step = '初始化扫描引擎'
        db.commit()

        # ===== 步骤 2: 加载规则 (progress: 10-20%) =====
        task.progress = 10
        task.current_step = '加载检测规则'
        db.commit()

        engine = ScanEngine()

        task.progress = 20
        db.commit()

        # ===== 步骤 3: 执行检测器 (progress: 20-80%) =====
        all_vulnerabilities = []
        progress_per_detector = 60 / len(DETECTORS)  # 60% 分配给检测器

        for i, detector_info in enumerate(DETECTORS):
            detector_name = detector_info['name']

            # 更新进度
            task.current_step = detector_name
            task.progress = 20 + int(i * progress_per_detector)
            db.commit()

            # 执行检测
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
                # 继续执行其他检测器

            # 完成该检测器
            task.progress = 20 + int((i + 1) * progress_per_detector)
            db.commit()

        # ===== 步骤 4: 计算评分 (progress: 80%) =====
        task.current_step = '计算安全评分'
        task.progress = 80
        db.commit()

        result = ScanEngine().scan(task_id, url, headers, param_name)

        # ===== 步骤 5: 保存漏洞 (progress: 90%) =====
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

        # ===== 步骤 6: 完成 (progress: 100%) =====
        task.status = 'completed'
        task.progress = 100
        task.current_step = '扫描完成'
        task.score = result.score
        task.level = result.level
        task.completed_at = datetime.utcnow()
        db.commit()
        db.close()

        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'task_id': task_id,
                'score': result.score,
                'level': result.level,
                'vulnerabilities': all_vulnerabilities,
                'score_breakdown': result.score_breakdown,
            }
        })

    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"Execute scan error: {error_detail}")

        # 更新失败状态（不使用 error_message 字段）
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

        # 返回真实错误（不返回 fallback 模拟数据）
        return jsonify({
            'code': 1,
            'message': f'扫描执行失败: {str(e)}',
            'data': {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
        }), 500


# Vercel 入口
handler = app