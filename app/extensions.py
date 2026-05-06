"""
Flask 扩展模块
全局扩展对象，延迟初始化
"""

from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

# 数据库扩展
db = SQLAlchemy()

# WebSocket 扩展
socketio = SocketIO()