"""
003 向量库注入检测器
高危漏洞：-15 分/个
检测方式：仅检测 API 是否存在，不进行写入操作
"""

import aiohttp
from typing import Dict, List

from .base import BaseDetector


class VectorInjectionDetector(BaseDetector):
    """向量库注入检测器"""

    SEVERITY = "critical"
    SCORE_DEDUCTION = 15
    RULE_ID = "RAG-SEC-003"

    VECTOR_ENDPOINTS = [
        "/api/vector",
        "/api/vectors",
        "/api/embeddings",
        "/api/retrieve",
        "/api/search",
        "/api/rag/query",
    ]

    async def detect(self, target_type: str, target_value: str, task_id: str = "unknown") -> List[Dict]:
        """
        执行向量库注入检测

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

        # 检测向量 API 是否存在
        for endpoint in self.VECTOR_ENDPOINTS:
            try:
                await self.rate_limiter.acquire(base_url)

                url = f"{base_url}{endpoint}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        # 记录审计日志
                        await self.log_request(
                            task_id=task_id,
                            request_url=url,
                            request_method="GET",
                            response_status=response.status,
                        )

                        # 如果 API 存在（返回 200 或 401/403），记录潜在风险
                        if response.status in [200, 401, 403]:
                            vulnerabilities.append(
                                self.create_vulnerability(
                                    vuln_id=f"vuln_vector_{len(vulnerabilities)}",
                                    name="向量库注入风险",
                                    description=f"检测到向量库 API {endpoint} 存在，需防范注入攻击",
                                    suggestion="对向量查询进行参数验证和转义，限制查询复杂度",
                                    evidence=[f"URL: {url}", f"Status: {response.status}"],
                                )
                            )
                            break  # 找到一个即可
            except Exception as e:
                # 记录错误，不中断检测
                await self.log_error(task_id, f"Endpoint {endpoint}: {str(e)}")
                continue

        return vulnerabilities