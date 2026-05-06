"""
Flask 应用工厂
"""

from flask import Flask
from flask_cors import CORS

from .config import load_config, TEMPLATES_DIR, AUDIT_LOG_DIR
from .extensions import db, socketio

from scanner.engine import ScanEngine
from scanner.scorer import VulnerabilityScorer
from scanner.auditor import ScanAuditor


def create_app(config_name: str = "default") -> Flask:
    """
    Flask 应用工厂函数

    Args:
        config_name: 配置名称（default, development, production）

    Returns:
        Flask: Flask 应用实例
    """
    # 创建 Flask 应用
    app = Flask(__name__, template_folder=str(TEMPLATES_DIR))

    # 加载配置
    app.config.update(load_config(config_name))

    # 初始化扩展
    CORS(app)
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    # 初始化数据库表
    with app.app_context():
        db.create_all()
        print("[DB] Database tables initialized")

    # 注册蓝图
    from .routes.pages import pages_bp
    from .routes.scan import scan_bp
    from .routes.report import report_bp
    from .routes.admin import admin_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(scan_bp, url_prefix="/api/v1/scan")
    app.register_blueprint(report_bp, url_prefix="/api/v1/report")
    app.register_blueprint(admin_bp, url_prefix="/api/v1/admin")

    # 注册 WebSocket 事件处理
    from .routes import pages_bp
    register_socket_events(socketio)

    # 注册错误处理
    register_error_handlers(app)

    # 初始化扫描引擎组件（设置审计日志目录）
    from .services.scan_service import ScanService
    scan_service = ScanService()
    scan_service.engine.auditor.log_dir = AUDIT_LOG_DIR

    print(f"[App] Application initialized with config: {config_name}")
    return app


def register_socket_events(socketio):
    """注册 WebSocket 事件处理"""

    @socketio.on("connect")
    def handle_connect():
        print(f"Client connected")

    @socketio.on("disconnect")
    def handle_disconnect():
        print(f"Client disconnected")

    @socketio.on("subscribe")
    def handle_subscribe(data):
        task_id = data.get("task_id")
        if task_id:
            print(f"Client subscribed to {task_id}")


def register_error_handlers(app):
    """注册错误处理"""

    @app.errorhandler(404)
    def not_found(error):
        return {"code": 1, "message": "接口不存在"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {"code": 1, "message": "服务器内部错误"}, 500