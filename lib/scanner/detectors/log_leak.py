"""
007 日志泄露检测器
中危漏洞：-10 分/个
"""

import aiohttp
from typing import Dict, List

from .base import BaseDetector


class LogLeakDetector(BaseDetector):
    """日志泄露检测器"""

    SEVERITY = "high"
    SCORE_DEDUCTION = 10
    RULE_ID = "RAG-SEC-007"

    LOG_PATHS = [
        "/logs",
        "/var/log",
        "/debug/logs",
        "/api/logs",
        "/logs/access.log",
        "/logs/error.log",
        "/admin/logs",
        "/.logs",
    ]

    async def detect(self, target_type: str, target_value: str, task_id: str = "unknown") -> List[Dict]:
        """
        执行日志泄露检测

        Args:
            target_type: 目标类型
            target_value: 目标 URL
            task_id: 任务 ID

        Returns:
            List[Dict]: 检测到的漏洞列表
        """
        vulnerabilities = []

        if not self.should_check_target(target_type):
            return vulnerabilities

        base_url = self.normalize_url(target_value)

        for path in self.LOG_PATHS:
            try:
                await self.rate_limiter.acquire(base_url)

                url = f"{base_url}{path}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        # 记录审计日志
                        await self.log_request(
                            task_id=task_id,
                            request_url=url,
                            request_method="GET",
                            response_status=response.status,
                        )

                        # 如果返回 200 且有内容，可能存在日志泄露
                        if response.status == 200:
                            text = await response.text()
                            if len(text) > 100:  # 有实际内容
                                vulnerabilities.append(
                                    self.create_vulnerability(
                                        vuln_id=f"vuln_log_leak_{len(vulnerabilities)}",
                                        name="日志泄露",
                                        description=f"日志路径 {path} 可公开访问，可能泄露敏感信息",
                                        suggestion="限制日志目录访问权限，配置 Web 服务器禁止访问日志文件",
                                        evidence=[f"URL: {url}", f"Status: {response.status}"],
                                    )
                                )
            except Exception as e:
                await self.log_error(task_id, f"Path {path}: {str(e)}")
                continue

        return vulnerabilities