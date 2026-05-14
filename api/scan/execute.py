"""
API 入口 - 执行扫描任务（分步更新进度）
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


def update_progress(db, task_id, status, progress, current_step, score=None, level=None, error=None):
    """更新任务进度（辅助函数）"""
    from lib.db import ScanTask
    task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
    if task:
        task.status = status
        task.progress = progress
        task.current_step = current_step
        if score is not None:
            task.score = score
        if level is not None:
            task.level = level
        if error is not None:
            task.error_message = error
        if status == 'completed':
            task.completed_at = datetime.utcnow()
        db.commit()
    return task


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
    from lib.db import get_session, init_db
    from scanner.engine import ScanEngine
    from scanner.scorer import Scorer

    # 初始化数据库
    init_db()
    db = get_session()

    if not db:
        return jsonify({'code': 1, 'message': 'Database connection failed'}), 500

    try:
        # ===== 步骤 1: 初始化 (progress: 5%) =====
        update_progress(db, task_id, 'running', 5, '初始化扫描引擎')

        # ===== 步骤 2: 加载规则 (progress: 10-20%) =====
        update_progress(db, task_id, 'running', 10, '加载检测规则')

        engine = ScanEngine()

        update_progress(db, task_id, 'running', 20, '规则加载完成')

        # ===== 步骤 3: 执行检测器 (progress: 20-80%) =====
        all_vulnerabilities = []
        failed_detectors = []
        progress_per_detector = 60 / len(DETECTORS)  # 60% 分配给检测器

        for i, detector_info in enumerate(DETECTORS):
            detector_name = detector_info['name']
            detector_key = detector_info['key']

            # 更新进度
            current_progress = 20 + int(i * progress_per_detector)
            update_progress(db, task_id, 'running', current_progress, detector_name)

            # 执行检测
            try:
                detector = engine.get_detector(detector_key)
                if detector:
                    vulns = detector.detect(url, headers, param_name)
                    if vulns:
                        all_vulnerabilities.extend(vulns)
            except Exception as e:
                print(f"Detector {detector_name} failed: {e}")
                failed_detectors.append(detector_name)
                # 继续执行其他检测器

            # 完成该检测器
            update_progress(db, task_id, 'running',
                           20 + int((i + 1) * progress_per_detector),
                           f'{detector_name}完成')

        # ===== 步骤 4: 计算评分 (progress: 80%) =====
        update_progress(db, task_id, 'running', 80, '计算安全评分')

        scorer = Scorer()
        score = scorer.calculate(all_vulnerabilities)
        level = scorer.get_level(score)

        # ===== 步骤 5: 保存漏洞 (progress: 90%) =====
        update_progress(db, task_id, 'running', 90, '保存检测结果')

        from lib.db import Vulnerability
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
        update_progress(db, task_id, 'completed', 100, '扫描完成', score, level)
        db.close()

        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'task_id': task_id,
                'score': score,
                'level': level,
                'vulnerabilities': all_vulnerabilities,
                'failed_detectors': failed_detectors,
            }
        })

    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"Execute scan error: {error_detail}")

        # 更新数据库失败状态
        update_progress(db, task_id, 'failed', 0, '扫描失败', error=str(e))
        db.close()

        # 返回真实错误（不是 fallback）
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