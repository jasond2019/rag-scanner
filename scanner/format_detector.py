"""
API 格式探测器
整合 ffuf 探测和 curl 解析
"""

import asyncio
import time
import re
from typing import Dict, Optional
from pathlib import Path

from .ffuf_wrapper import FfufWrapper
from .curl_parser import CurlParser


class APIFormatDetector:
    """API 格式探测器 - 整合 ffuf 和 curl 解析"""

    def __init__(self, wordlists_dir: str = "wordlists"):
        self.ffuf = FfufWrapper(wordlists_dir)
        self.curl_parser = CurlParser()

    async def detect(self, user_input: str) -> Dict:
        """
        检测 API 格式

        Args:
            user_input: 用户输入（URL 或 curl 命令）

        Returns:
            {
                "input_type": "url" | "curl",
                "url": "http://...",
                "method": "POST",
                "param_name": "query",
                "headers": {...},
                "extra_params": {...},
                "confidence": 0.9,
                "probe_time": 2.5,
            }
        """

        input_lower = user_input.strip().lower()

        # curl 命令：直接解析
        if input_lower.startswith("curl "):
            return await self._detect_from_curl(user_input)

        # URL：使用 ffuf 探测
        if user_input.strip().startswith(("http://", "https://")):
            return await self._detect_from_url(user_input.strip())

        # 默认当作 URL
        return await self._detect_from_url(user_input.strip())

    async def _detect_from_curl(self, curl_cmd: str) -> Dict:
        """从 curl 命令解析格式"""

        try:
            parsed = self.curl_parser.parse(curl_cmd)
            validation = self.curl_parser.validate(parsed)

            result = {
                "input_type": "curl",
                "url": parsed["url"],
                "method": parsed["method"],
                "param_name": parsed["param_name"] or "query",
                "headers": parsed["headers"],
                "extra_params": parsed["extra_params"],
                "body_raw": parsed["body_raw"],
                "confidence": 1.0,  # curl 解析置信度最高
                "probe_time": 0,
                "validation": validation,
            }

            # 确保有 Content-Type
            if "Content-Type" not in result["headers"]:
                result["headers"]["Content-Type"] = "application/json"

            return result

        except Exception as e:
            # curl 解析失败，尝试提取 URL 并探测
            url = self._extract_url_from_failed_curl(curl_cmd)
            if url:
                return await self._detect_from_url(url)

            # 完全失败，返回默认
            raise ValueError(f"Failed to parse curl command: {e}")

    def _extract_url_from_failed_curl(self, curl_cmd: str) -> Optional[str]:
        """从失败的 curl 解析中提取 URL"""
        url_match = re.search(r'https?://[^\s\'"<>]+', curl_cmd)
        if url_match:
            return url_match.group(0)
        return None

    async def _detect_from_url(self, url: str) -> Dict:
        """使用 ffuf 探测 URL"""

        start_time = time.time()

        # 调用 ffuf 探测
        probe_result = await self.ffuf.detect_param_name(url)

        probe_time = time.time() - start_time

        result = {
            "input_type": "url",
            "url": url,
            "method": probe_result.get("method", "POST"),
            "param_name": probe_result.get("param_name", "query"),
            "headers": {"Content-Type": "application/json"},
            "extra_params": {},
            "confidence": probe_result.get("confidence", 0.5),
            "probe_time": round(probe_time, 2),
            "probe_response": probe_result.get("probe_response", {}),
            "ffuf_available": self.ffuf.is_available(),
        }

        return result

    def parse_curl_preview(self, curl_cmd: str) -> Dict:
        """
        快速解析 curl 预览（用于前端显示，不抛异常）
        """
        return self.curl_parser.get_preview(curl_cmd)

    def check_ffuf_installation(self) -> Dict:
        """检查 ffuf 安装状态"""
        return self.ffuf.check_installation()

    def get_request_format(self, detection_result: Dict) -> Dict:
        """
        从检测结果提取请求格式（供检测器使用）

        Returns:
            {
                "method": "POST",
                "param_name": "query",
                "headers": {...},
                "extra_params": {...},
            }
        """
        return {
            "method": detection_result.get("method", "POST"),
            "param_name": detection_result.get("param_name", "query"),
            "headers": detection_result.get("headers", {"Content-Type": "application/json"}),
            "extra_params": detection_result.get("extra_params", {}),
        }