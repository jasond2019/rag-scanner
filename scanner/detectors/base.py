"""
检测器基类
提供统一的抽象接口和共享工具方法
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import aiohttp


class BaseDetector(ABC):
    """检测器抽象基类"""

    # 子类必须定义的类属性
    SEVERITY: str = "medium"
    SCORE_DEDUCTION: int = 5
    RULE_ID: str = ""

    def __init__(self, rate_limiter, auditor):
        """
        初始化检测器

        Args:
            rate_limiter: 速率限制器实例
            auditor: 审计日志记录器实例
        """
        self.rate_limiter = rate_limiter
        self.auditor = auditor

        # 新增：请求格式配置（由 ScanEngine 设置）
        self._request_format: Dict = {
            "method": "POST",
            "param_name": "prompt",
            "headers": {"Content-Type": "application/json"},
            "extra_params": {},
        }

    @abstractmethod
    async def detect(self, target_type: str, target_value: str, task_id: str = "unknown") -> List[Dict]:
        """
        执行在线检测

        Args:
            target_type: 目标类型 (url, endpoint, config)
            target_value: 目标 URL 或配置内容
            task_id: 任务 ID

        Returns:
            List[Dict]: 检测到的漏洞列表
        """
        pass

    async def detect_config(self, config_data: Dict, task_id: str = "unknown") -> List[Dict]:
        """
        执行配置文件检测（默认不支持，子类可覆盖）

        Args:
            config_data: 配置文件数据
            task_id: 任务 ID

        Returns:
            List[Dict]: 检测到的漏洞列表
        """
        return []

    # ==================== 共享工具方法 ====================

    def create_vulnerability(
        self,
        vuln_id: str,
        name: str,
        description: str,
        suggestion: str,
        evidence: List[str],
        extra: Optional[Dict] = None
    ) -> Dict:
        """
        创建标准化的漏洞结构

        Args:
            vuln_id: 漏洞唯一 ID
            name: 漏洞名称
            description: 漏洞描述
            suggestion: 修复建议
            evidence: 证据列表
            extra: 额外字段

        Returns:
            Dict: 标准化的漏洞字典
        """
        vuln = {
            "id": vuln_id,
            "rule_id": self.RULE_ID,
            "type": self._get_vuln_type(),
            "name": name,
            "severity": self.SEVERITY,
            "score_deduction": self.SCORE_DEDUCTION,
            "description": description,
            "suggestion": suggestion,
            "evidence": evidence,
        }
        if extra:
            vuln.update(extra)
        return vuln

    def _get_vuln_type(self) -> str:
        """从 RULE_ID 提取漏洞类型"""
        if self.RULE_ID:
            # RAG-SEC-001 -> prompt_injection
            parts = self.RULE_ID.split("-")
            if len(parts) >= 3:
                return parts[-1].lower()
        return self.__class__.__name__.replace("Detector", "").lower()

    async def safe_http_request(
        self,
        url: str,
        method: str = "GET",
        timeout: int = 5,
        **kwargs
    ) -> tuple:
        """
        安全的 HTTP 请求包装

        Args:
            url: 请求 URL
            method: HTTP 方法
            timeout: 超时时间（秒）
            **kwargs: 其他请求参数

        Returns:
            tuple: (status_code, response_text) 或 (None, error_message)
        """
        try:
            await self.rate_limiter.acquire(url)

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    **kwargs
                ) as response:
                    return response.status, await response.text()

        except Exception as e:
            return None, str(e)

    async def log_request(
        self,
        task_id: str,
        request_url: str,
        request_method: str,
        request_payload: Optional[str] = None,
        response_status: Optional[int] = None,
        response_body: Optional[str] = None
    ) -> None:
        """
        记录请求审计日志

        Args:
            task_id: 任务 ID
            request_url: 请求 URL
            request_method: 请求方法
            request_payload: 请求体
            response_status: 响应状态码
            response_body: 响应体
        """
        await self.auditor.log_request(
            task_id=task_id,
            detector=self.RULE_ID,
            request_url=request_url,
            request_method=request_method,
            request_payload=request_payload,
            response_status=response_status or 0,
            response_body=response_body[:500] if response_body else None,
        )

    async def log_error(self, task_id: str, error_message: str) -> None:
        """
        记录错误日志

        Args:
            task_id: 任务 ID
            error_message: 错误信息
        """
        await self.auditor.log_error(
            task_id=task_id,
            detector=self.RULE_ID,
            error=error_message
        )

    def should_check_target(self, target_type: str) -> bool:
        """
        检查目标类型是否需要检测

        Args:
            target_type: 目标类型

        Returns:
            bool: 是否需要检测
        """
        # 默认只检测 url 和 endpoint 类型
        return target_type in ["url", "endpoint"]

    def normalize_url(self, target_value: str) -> str:
        """
        标准化 URL（移除尾部斜杠）

        Args:
            target_value: 目标 URL

        Returns:
            str: 标准化后的 URL
        """
        return target_value.rstrip('/')

    # ==================== 请求格式支持（新增） ====================

    def set_request_format(self, format_config: Dict):
        """
        设置请求格式

        Args:
            format_config: {
                "method": "POST",
                "param_name": "query",
                "headers": {...},
                "extra_params": {...},
            }
        """
        self._request_format = format_config

    async def send_payload(self, url: str, payload: str) -> tuple:
        """
        使用配置格式发送 payload

        Args:
            url: 目标 URL
            payload: payload 内容

        Returns:
            (status_code, response_text)
        """
        method = self._request_format.get("method", "POST")
        param_name = self._request_format.get("param_name", "query")
        headers = self._request_format.get("headers", {})
        extra_params = self._request_format.get("extra_params", {})

        # 构建请求体
        body = {param_name: payload}
        body.update(extra_params)  # 保持原始请求结构

        await self.rate_limiter.acquire(url)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    json=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    return response.status, await response.text()
        except Exception as e:
            return None, str(e)

    async def send_payload_with_log(self, url: str, payload: str, task_id: str) -> tuple:
        """
        发送 payload 并记录审计日志

        Args:
            url: 目标 URL
            payload: payload 内容
            task_id: 任务 ID

        Returns:
            (status_code, response_text)
        """
        status, response = await self.send_payload(url, payload)

        # 记录审计日志
        await self.log_request(
            task_id=task_id,
            request_url=url,
            request_method=self._request_format.get("method", "POST"),
            request_payload=payload,
            response_status=status or 0,
            response_body=response[:500] if response else None,
        )

        return status, response