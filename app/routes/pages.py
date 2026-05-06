"""
页面路由
"""

from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    """首页"""
    return render_template("index.html")


@pages_bp.route("/report/<task_id>")
def report_page(task_id):
    """报告页面"""
    return render_template("report.html", task_id=task_id)


@pages_bp.route("/admin")
def admin_page():
    """管理页面"""
    return render_template("admin.html")