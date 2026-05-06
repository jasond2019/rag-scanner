"""
管理 API 路由
Version: 2.1 - 添加任务详情展开功能，调整路由顺序
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

from ..services.persistence import PersistenceService
from ..services.scan_service import ScanService
from ..models import ScanTask, Vulnerability, ScanAuditLog
from ..extensions import db

admin_bp = Blueprint("admin", __name__)


def get_persistence():
    """获取持久化服务实例（延迟初始化）"""
    return PersistenceService()


def get_scan_service():
    """获取扫描服务实例（延迟初始化）"""
    return ScanService()


@admin_bp.route("/stats", methods=["GET"])
def get_stats():
    """
    获取统计数据

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "total_scans": 100,
                "completed_scans": 80,
                "avg_score": 75,
                "critical_vulns": 5,
                "today_scans": 10
            }
        }
    """
    try:
        # 获取总扫描数
        total = ScanTask.query.count()

        # 获取已完成扫描数
        completed = ScanTask.query.filter_by(status="completed").count()

        # 获取已完成任务的分数
        completed_tasks = ScanTask.query.filter_by(status="completed").all()
        scores = [t.score for t in completed_tasks if t.score is not None]
        avg_score = round(sum(scores) / len(scores)) if scores else 0

        # 获取严重漏洞数
        critical = Vulnerability.query.filter_by(severity="critical").count()

        # 计算今日扫描数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_scans = ScanTask.query.filter(ScanTask.created_at >= today_start).count()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "total_scans": total,
                "completed_scans": completed,
                "avg_score": avg_score,
                "critical_vulns": critical,
                "today_scans": today_scans,
            }
        })
    except Exception as e:
        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "total_scans": 0,
                "completed_scans": 0,
                "avg_score": 0,
                "critical_vulns": 0,
                "today_scans": 0,
            }
        })


@admin_bp.route("/tasks", methods=["GET"])
def get_tasks():
    """
    获取任务列表

    Query params:
        limit: 最大返回数量（默认 20）

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "tasks": [...]
            }
        }
    """
    limit = int(request.args.get("limit", 20))

    try:
        persistence = get_persistence()
        tasks = persistence.get_recent_tasks(limit)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "tasks": tasks
            }
        })
    except Exception as e:
        return jsonify({
            "code": 1,
            "message": f"获取任务列表失败: {str(e)}"
        }), 500


@admin_bp.route("/tasks/in-progress", methods=["GET"])
def get_in_progress_tasks():
    """
    获取用户进行中的任务（用于页面刷新恢复）

    Query params:
        user_id: 用户 ID（匿名用户 ID）

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "tasks": [...]
            }
        }
    """
    user_id = request.args.get("user_id")

    try:
        persistence = get_persistence()

        if user_id:
            # 查询该用户进行中和排队的任务
            tasks = persistence.get_user_in_progress_tasks(user_id)
        else:
            # 如果没有 user_id，返回所有进行中的任务
            tasks = persistence.get_all_in_progress_tasks()

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "tasks": tasks
            }
        })
    except Exception as e:
        return jsonify({
            "code": 1,
            "message": f"获取进行中任务失败: {str(e)}"
        }), 500


@admin_bp.route("/tasks/history", methods=["GET"])
def get_user_history():
    """
    获取用户扫描历史记录（已完成 + 进行中）

    Query params:
        user_id: 用户 ID（匿名用户 ID）
        limit: 最大返回数量（默认 10）

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "tasks": [...]
            }
        }
    """
    user_id = request.args.get("user_id")
    limit = int(request.args.get("limit", 10))

    try:
        persistence = get_persistence()

        if user_id:
            # 查询该用户的所有任务（按时间倒序）
            tasks = persistence.get_user_tasks(user_id, limit)
        else:
            # 如果没有 user_id，返回最近的任务
            tasks = persistence.get_recent_tasks(limit)

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "tasks": tasks
            }
        })
    except Exception as e:
        return jsonify({
            "code": 1,
            "message": f"获取历史记录失败: {str(e)}"
        }), 500


@admin_bp.route("/tasks/<task_id>/detail", methods=["GET"])
def get_task_detail(task_id):
    """
    获取任务详情（含检测器分组和审计日志）

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "task": {...},
                "score_breakdown": {...},
                "detectors": [...],
                "vulnerability_count": 3
            }
        }
    """
    try:
        persistence = get_persistence()
        detail = persistence.get_task_detail(task_id)

        if not detail:
            return jsonify({
                "code": 1,
                "message": "任务不存在"
            }), 404

        return jsonify({
            "code": 0,
            "message": "success",
            "data": detail
        })
    except Exception as e:
        return jsonify({
            "code": 1,
            "message": f"获取任务详情失败: {str(e)}"
        }), 500


@admin_bp.route("/tasks/<task_id>/logs", methods=["GET"])
def get_task_logs(task_id):
    """
    获取任务审计日志

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "logs": [...],
                "log_file": "..."
            }
        }
    """
    scan_service = get_scan_service()
    result = scan_service.get_task_logs(task_id)
    return jsonify(result)