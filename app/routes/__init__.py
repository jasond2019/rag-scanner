"""
路由模块
"""

from .pages import pages_bp
from .scan import scan_bp
from .report import report_bp
from .admin import admin_bp

__all__ = [
    "pages_bp",
    "scan_bp",
    "report_bp",
    "admin_bp",
]