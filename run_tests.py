#!/usr/bin/env python3
"""
测试运行脚本
"""

import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).parent
    
    print("=" * 60)
    print("🧪 RAG Scanner 测试套件")
    print("=" * 60)
    
    # 运行 pytest
    test_dir = project_root / "tests"
    
    if not test_dir.exists():
        print("❌ 测试目录不存在")
        return 1
    
    print(f"\n📁 测试目录：{test_dir}")
    print("\n运行测试...\n")
    
    # 检查依赖
    try:
        import pytest
        print("✅ pytest 已安装")
    except ImportError:
        print("❌ pytest 未安装，请先运行：pip install pytest pytest-asyncio")
        return 1
    
    # 运行测试
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        str(test_dir),
        "-v",
        "--tb=short"
    ], cwd=project_root)
    
    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败")
    print("=" * 60)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
