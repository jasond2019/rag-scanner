#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Scanner 入口文件
使用 Flask 应用工厂模式
Version: 2.1 - 添加任务详情展开功能
"""

from pathlib import Path
import sys

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 强制清除所有相关缓存模块，确保使用最新代码
modules_to_clear = []
for module_name in list(sys.modules.keys()):
    if any(keyword in module_name for keyword in ['app', 'scanner', 'persistence', 'admin', 'routes', 'services', 'models', 'extensions']):
        modules_to_clear.append(module_name)

for module_name in modules_to_clear:
    del sys.modules[module_name]

print(f"[Main] Cleared {len(modules_to_clear)} cached modules")

from app import create_app
from app.extensions import socketio

# 创建 Flask 应用
app = create_app()


if __name__ == "__main__":
    print("=" * 50)
    print("  RAG Scanner - Starting Server")
    print("=" * 50)
    print()
    print(f"  Access: http://localhost:5000")
    print(f"  Admin:  http://localhost:5000/admin")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 50)

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False,  # SQLite + 双进程重载可能导致问题
        allow_unsafe_werkzeug=True,
    )