"""
健康检查 API - 系统状态监控
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import time
from datetime import datetime

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, api_dir)

app = Flask(__name__)
CORS(app)

VERSION = "1.0.0"


@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """
    系统健康检查

    Response:
        {
            "code": 0,
            "data": {
                "status": "healthy" | "degraded" | "unhealthy",
                "checks": {
                    "database": {"status": "connected", "latency_ms": 5},
                    "detectors": {"status": "ready", "count": 10}
                },
                "version": "1.0.0",
                "timestamp": "..."
            }
        }
    """
    if request.method == 'OPTIONS':
        return jsonify({'code': 0}), 200

    status = {
        "status": "healthy",
        "checks": {}
    }

    # === 检查数据库 ===
    try:
        from lib.db import get_session, init_db

        init_db()
        start_time = time.time()
        db = get_session()

        if db:
            # 执行简单查询测试连接
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            latency = int((time.time() - start_time) * 1000)
            db.close()

            status["checks"]["database"] = {
                "status": "connected",
                "latency_ms": latency
            }
        else:
            status["checks"]["database"] = {"status": "disconnected"}
            status["status"] = "degraded"

    except Exception as e:
        status["checks"]["database"] = {
            "status": "error",
            "message": str(e)[:100]
        }
        status["status"] = "unhealthy"

    # === 检查检测器 ===
    try:
        from scanner.engine import ScanEngine
        engine = ScanEngine()

        status["checks"]["detectors"] = {
            "status": "ready",
            "count": len(engine.detectors)
        }
    except Exception as e:
        status["checks"]["detectors"] = {
            "status": "error",
            "message": str(e)[:100]
        }
        status["status"] = "degraded"

    # === 检查评分器 ===
    try:
        from scanner.scorer import VulnerabilityScorer
        scorer = VulnerabilityScorer()

        # 测试评分计算
        test_result = scorer.calculate_breakdown([])

        status["checks"]["scorer"] = {
            "status": "ready",
            "test_score": test_result["final_score"]
        }
    except Exception as e:
        status["checks"]["scorer"] = {
            "status": "error",
            "message": str(e)[:100]
        }
        status["status"] = "degraded"

    # 版本和时间戳
    status["version"] = VERSION
    status["timestamp"] = datetime.utcnow().isoformat() + "Z"

    # 返回码
    code = 0 if status["status"] == "healthy" else 1

    return jsonify({"code": code, "data": status})


# Vercel 入口
handler = app