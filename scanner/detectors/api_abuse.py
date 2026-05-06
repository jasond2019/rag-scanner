"""
006 API 滥用检测器
中危漏洞：-10 分/个
检测方式：检测 Rate Limit 是否存在，不进行压力测试
"""

import aiohttp
import asyncio
import time
from typing import Dict, List

from .base import BaseDetector


class APIAbuseDetector(BaseDetector):
    """API 滥用检测器"""

    SEVERITY = "high"
    SCORE_DEDUCTION = 10
    RULE_ID = "RAG-SEC-006"

    async def detect(self, target_type: str, target_value: str, task_id: str = "unknown") -> List[Dict]:
        """
        执行 API 滥用检测

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

        # 直接使用目标 URL（不拼接额外路径）
        url = self.normalize_url(target_value)
        response_times = []
        rate_limited = False

        # 获取请求格式配置
        param_name = self._request_format.get("param_name", "query")
        headers = self._request_format.get("headers", {"Content-Type": "application/json"})

        # 发送 5 个快速请求检测速率限制
        for i in range(5):
            try:
                await self.rate_limiter.acquire(url)

                start = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json={param_name: f"rate_limit_test_{i}"},
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        elapsed = time.time() - start
                        response_times.append(elapsed)

                        # 记录审计日志
                        await self.log_request(
                            task_id=task_id,
                            request_url=url,
                            request_method="POST",
                            request_payload=f"rate_limit_test_{i}",
                            response_status=response.status,
                        )

                        # 检测是否返回 429（速率限制）
                        if response.status == 429:
                            rate_limited = True
                            break

                # 快速连续发送
                if i < 4:
                    await asyncio.sleep(0.1)

            except Exception as e:
                # 记录错误但不中断整个检测流程
                await self.log_error(task_id, str(e))
                continue

        # 如果没有速率限制，记录风险
        if not rate_limited and len(response_times) >= 3:
            avg_time = sum(response_times) / len(response_times)
            vulnerabilities.append(
                self.create_vulnerability(
                    vuln_id=f"vuln_api_abuse_{len(vulnerabilities)}",
                    name="API 滥用风险",
                    description=f"API 未检测到速率限制机制，可能被滥用",
                    suggestion="实施速率限制（如每分钟 60 请求），添加请求频率监控",
                    evidence=[f"URL: {url}", f"Avg Response: {avg_time:.2f}s", "No rate limit detected"],
                )
            )

        return vulnerabilities