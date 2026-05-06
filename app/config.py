"""
应用配置模块
集中管理所有配置项
"""

import os
from pathlib import Path

# ==================== 项目路径配置 ====================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSTANCE_DIR = PROJECT_ROOT / "instance"
DATA_DIR = PROJECT_ROOT / "data"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# 确保目录存在
INSTANCE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ==================== 文件路径配置 ====================

DATABASE_PATH = INSTANCE_DIR / "scanner.db"
UPLOAD_FOLDER = DATA_DIR / "uploads"
REPORTS_FOLDER = PROJECT_ROOT / "reports"
AUDIT_LOG_DIR = DATA_DIR / "audit_logs"

# 确保目录存在
UPLOAD_FOLDER.mkdir(exist_ok=True)
REPORTS_FOLDER.mkdir(exist_ok=True)
AUDIT_LOG_DIR.mkdir(exist_ok=True)


# ==================== 配置加载函数 ====================

def load_config(config_name: str = "default") -> dict:
    """
    加载应用配置

    Args:
        config_name: 配置名称（default, development, production）

    Returns:
        dict: 配置字典
    """
    # SQLite 路径（Windows 下反斜杠需要转换）
    _sqlite_path = str(DATABASE_PATH).replace("\\", "/")

    config = {
        "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"),
        "SQLALCHEMY_DATABASE_URI": os.environ.get(
            "DATABASE_URL",
            f"sqlite:///{_sqlite_path}"
        ),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "UPLOAD_FOLDER": str(UPLOAD_FOLDER),
        "REPORTS_FOLDER": str(REPORTS_FOLDER),
        "AUDIT_LOG_DIR": str(AUDIT_LOG_DIR),
    }

    # 生产环境额外配置
    if config_name == "production":
        config["DEBUG"] = False
        config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "CHANGE-THIS-IN-PRODUCTION")

    return config


# ==================== 评分配置 ====================

class ScoringConfig:
    """评分规则配置"""

    BASE_SCORE = 100

    SEVERITY_DEDUCTIONS = {
        "critical": 15,  # 高危
        "high": 10,      # 中危
        "medium": 5,     # 低危
        "low": 2,        # 轻微
    }

    RISK_THRESHOLDS = {
        "high": (0, 69),      # 高风险（红色）
        "medium": (70, 89),   # 中等风险（黄色）
        "low": (90, 100),     # 低风险（绿色）
    }


# ==================== 检测器配置 ====================

class DetectorConfig:
    """检测器配置"""

    # 检测器执行顺序（高危优先）
    ORDER = [
        "prompt_injection",      # -15
        "data_leak",             # -15
        "vector_injection",      # -15
        "retrieval_pollution",   # -15
        "auth_bypass",           # -10
        "api_abuse",             # -10
        "log_leak",              # -10
        "model_jailbreak",       # -10
        "dependency_check",      # -5
        "config_check",          # -5
    ]

    # 速率限制配置
    MAX_REQUESTS_PER_SECOND = 10
    REQUEST_TIMEOUT = 5