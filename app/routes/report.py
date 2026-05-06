"""
报告 API 路由
"""

from flask import Blueprint, request, jsonify, send_file
import os

from ..services.report_service import ReportService

report_bp = Blueprint("report", __name__)


def get_report_service():
    """获取报告服务实例（延迟初始化）"""
    return ReportService()


@report_bp.route("/generate", methods=["POST", "GET"])
def generate_report():
    """
    生成 PDF 报告

    Request (POST):
        {
            "task_id": "..."
        }

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "report_id": "...",
                "download_url": "/api/v1/report/download/...",
                "expire_at": "..."
            }
        }
    """
    task_id = request.args.get("task_id") or (request.get_json() or {}).get("task_id")

    if not task_id:
        return jsonify({"code": 1, "message": "task_id 必填"}), 400

    report_service = get_report_service()
    result = report_service.generate_report(task_id)

    if result["code"] != 0:
        return jsonify(result), 404 if "不存在" in result["message"] else 400

    return jsonify(result)


@report_bp.route("/download/<report_id>", methods=["GET"])
def download_report(report_id):
    """
    下载 PDF/TXT 报告

    Response: 报告文件
    """
    report_service = get_report_service()
    report_path = report_service.get_report_path(report_id)

    if not report_path or not os.path.exists(report_path):
        return jsonify({"code": 1, "message": "报告不存在"}), 404

    # 根据实际文件扩展名设置下载名称
    ext = os.path.splitext(report_path)[1] or ".pdf"
    download_name = f"{report_id.rsplit('.', 1)[0] if '.' in report_id else report_id}{ext}"

    return send_file(report_path, as_attachment=True, download_name=download_name)