"""
005 权限绕过检测器
中危漏洞：-10 分/个
"""

import aiohttp
from typing import Dict, List

from .base import BaseDetector


class AuthBypassDetector(BaseDetector):
    """权限绕过检测器"""

    SEVERITY = "high"
    SCORE_DEDUCTION = 10
    RULE_ID = "RAG-SEC-005"

    ADMIN_PATHS = [
        "/api/admin",
        "/api/internal",
        "/admin/dashboard",
        "/api/users",
    ]

    TEST_HEADERS = [
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Real-IP": "127.0.0.1"},
        {"X-Original-URL": "/admin"},
    ]

    async def detect(self, target_type: str, target_value: str, task_id: str = "unknown") -> List[Dict]:
        """
        执行权限绕过检测

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

        for path in self.ADMIN_PATHS:
            for headers in self.TEST_HEADERS:
                try:
                    await self.rate_limiter.acquire(base_url)

                    url = f"{base_url}{path}"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                            # 记录审计日志
                            await self.log_request(
                                task_id=task_id,
                                request_url=url,
                                request_method="GET",
                                response_status=response.status,
                            )

                            # 如果返回 200，可能存在权限绕过
                            if response.status == 200:
                                vulnerabilities.append(
                                    self.create_vulnerability(
                                        vuln_id=f"vuln_auth_bypass_{len(vulnerabilities)}",
                                        name="权限绕过",
                                        description=f"管理路径 {path} 可能可通过 header 绕过访问控制",
                                        suggestion="验证所有请求的身份，不信任 X-Forwarded-For 等 header",
                                        evidence=[f"URL: {url}", f"Header: {headers}"],
                                    )
                                )
                                break
                except Exception as e:
                    # 记录错误，不中断检测
                    await self.log_error(task_id, f"Path {path} with headers {headers}: {str(e)}")
                    continue

        return vulnerabilities