"""
009 依赖漏洞检测器
低危漏洞：-5 分/个
检测方式：仅配置文件检测，识别已知 CVE
"""

import re
from typing import Dict, List

from .base import BaseDetector


class DependencyCheckDetector(BaseDetector):
    """依赖漏洞检测器"""

    SEVERITY = "medium"
    SCORE_DEDUCTION = 5
    RULE_ID = "RAG-SEC-009"

    KNOWN_VULNERABLE_PACKAGES = {
        "flask": {"safe_version": "2.0.0", "cve": "CVE-2023-30861"},
        "requests": {"safe_version": "2.25.0", "cve": "CVE-2023-32681"},
        "urllib3": {"safe_version": "1.26.0", "cve": "CVE-2023-45803"},
        "pillow": {"safe_version": "10.0.0", "cve": "CVE-2023-44271"},
        "numpy": {"safe_version": "1.22.0", "cve": "CVE-2021-41496"},
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

        # 检测 requirements.txt 内容
        if "requirements" in config_data:
            requirements = config_data["requirements"]
            for line in requirements.split("\n"):
                for pkg, info in self.KNOWN_VULNERABLE_PACKAGES.items():
                    if pkg.lower() in line.lower():
                        # 提取版本号
                        match = re.search(r'([<>=]+)\s*([\d.]+)', line)
                        if match:
                            version = match.group(2)
                            if self._is_version_vulnerable(pkg, version):
                                vulnerabilities.append(
                                    self.create_vulnerability(
                                        vuln_id=f"vuln_dep_{pkg}_{len(vulnerabilities)}",
                                        name="依赖漏洞",
                                        description=f"检测到易受攻击的 {pkg} 版本 ({version})，存在 {info['cve']}",
                                        suggestion=f"升级 {pkg} 到 {info['safe_version']} 或更高版本",
                                        evidence=[f"Package: {pkg}", f"Version: {version}", f"CVE: {info['cve']}"],
                                    )
                                )

        return vulnerabilities

    def _is_version_vulnerable(self, package: str, version: str) -> bool:
        """简单版本比较"""
        safe_version = self.KNOWN_VULNERABLE_PACKAGES.get(package, {}).get("safe_version")
        if not safe_version:
            return False

        try:
            v_parts = [int(x) for x in version.split(".")]
            s_parts = [int(x) for x in safe_version.split(".")]

            for v, s in zip(v_parts, s_parts):
                if v < s:
                    return True
                elif v > s:
                    return False
            return False
        except (ValueError, TypeError):
            return False