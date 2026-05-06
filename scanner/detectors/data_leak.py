"""
002 数据泄露检测器
高危漏洞：-15 分/个
"""

import aiohttp
from typing import Dict, List

from .base import BaseDetector


class DataLeakDetector(BaseDetector):
    """数据泄露检测器"""

    SEVERITY = "critical"
    SCORE_DEDUCTION = 15
    RULE_ID = "RAG-SEC-002"

    SENSITIVE_PATHS = [
        "/api/internal/config",
        "/admin/users",
        "/.env",
        "/api/debug",
        "/config.json",
        "/.git/config",
        "/wp-config.php",
        "/api/v1/admin",
    ]

    async def detect(self, target_type: str, target_value: str, task_id: str = "unknown") -> List[Dict]:
        """
        执行数据泄露检测

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

        for path in self.SENSITIVE_PATHS:
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

                        # 如果返回 200 且内容不为空，可能存在泄露
                        if response.status == 200:
                            text = await response.text()
                            if len(text) > 50:  # 有实际内容
                                vulnerabilities.append(
                                    self.create_vulnerability(
                                        vuln_id=f"vuln_data_leak_{len(vulnerabilities)}",
                                        name="数据泄露",
                                        description=f"敏感路径 {path} 可公开访问，可能存在数据泄露风险",
                                        suggestion="配置访问控制，限制敏感路径的访问权限",
                                        evidence=[f"URL: {url}", f"Status: {response.status}"],
                                    )
                                )
            except Exception as e:
                # 记录错误，不中断检测
                await self.log_error(task_id, f"Path {path}: {str(e)}")
                continue

        return vulnerabilities