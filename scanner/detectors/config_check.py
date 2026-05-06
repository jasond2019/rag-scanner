"""
010 配置错误检测器
低危漏洞：-5 分/个
"""

import re
import json
from typing import Dict, List

from .base import BaseDetector


class ConfigCheckDetector(BaseDetector):
    """配置错误检测器"""

    SEVERITY = "medium"
    SCORE_DEDUCTION = 5
    RULE_ID = "RAG-SEC-010"

    PATTERNS = {
        "default_password": [r"password.*[:=].*['\"]?(password|123456|admin|root)['\"]?"],
        "hardcoded_key": [r"(api_key|apikey|secret_key|access_key).*[:=].*['\"][a-zA-Z0-9]{16,}['\"]"],
        "debug_mode_enabled": [r"debug.*[:=].*(true|True|1)"],
        "cors_allow_all": [r"cors.*[:=].*['\"]\\*['\"]", r"ALLOWED_ORIGINS.*[:=].*['\"]\\*['\"]"],
        "weak_secret_key": [r"secret.*[:=].*['\"][a-z0-9]{8,16}['\"]"],
    }

    def __init__(self, auditor):
        """
        初始化检测器（不需要 rate_limiter）

        Args:
            auditor: 审计日志记录器实例
        """
        self.auditor = auditor
        # 不设置 rate_limiter，因为不进行在线检测

    async def detect(self, target_type: str, target_value: str, task_id: str = "unknown") -> List[Dict]:
        """
        在线检测（不支持）

        Args:
            target_type: 目标类型
            target_value: 目标 URL
            task_id: 任务 ID

        Returns:
            List[Dict]: 空列表
        """
        return []

    async def detect_config(self, config_data: Dict, task_id: str = "unknown") -> List[Dict]:
        """
        执行配置文件检测

        Args:
            config_data: 配置文件数据
            task_id: 任务 ID

        Returns:
            List[Dict]: 检测到的漏洞列表
        """
        vulnerabilities = []

        # 转换为 JSON 字符串进行匹配
        config_str = json.dumps(config_data, indent=2)

        for check_name, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, config_str, re.IGNORECASE)
                if matches:
                    vulnerabilities.append(
                        self.create_vulnerability(
                            vuln_id=f"vuln_config_{check_name}_{len(vulnerabilities)}",
                            name="配置错误",
                            description=f"检测到 {self._get_check_name(check_name)}",
                            suggestion=self._get_suggestion(check_name),
                            evidence=[f"Pattern: {pattern}"],
                        )
                    )
                    break

        return vulnerabilities

    def _get_check_name(self, check: str) -> str:
        """获取检查项的中文名称"""
        names = {
            "default_password": "默认密码或弱密码",
            "hardcoded_key": "硬编码的 API 密钥",
            "debug_mode_enabled": "调试模式已启用",
            "cors_allow_all": "CORS 配置为允许所有来源",
            "weak_secret_key": "密钥强度不足",
        }
        return names.get(check, check)

    def _get_suggestion(self, check: str) -> str:
        """获取修复建议"""
        suggestions = {
            "default_password": "修改为强密码，不要使用默认密码",
            "hardcoded_key": "使用环境变量或密钥管理服务存储密钥",
            "debug_mode_enabled": "生产环境请关闭调试模式",
            "cors_allow_all": "配置具体的允许来源列表",
            "weak_secret_key": "使用更长的随机密钥（至少 32 位）",
        }
        return suggestions.get(check, "检查并修复配置问题")