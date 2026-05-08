"""
Base Detector for Vercel Serverless
Simplified synchronous version
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import requests


class BaseDetector(ABC):
    """检测器基类"""

    SEVERITY: str = "medium"
    SCORE_DEDUCTION: int = 5
    RULE_ID: str = ""

    def __init__(self):
        self._request_format = {
            "method": "POST",
            "param_name": "query",
            "headers": {"Content-Type": "application/json"},
        }

    @abstractmethod
    def detect(self, target_url: str, headers: Dict, task_id: str) -> List[Dict]:
        """执行检测"""
        pass

    def set_request_format(self, format_config: Dict):
        """设置请求格式"""
        self._request_format = format_config

    def create_vulnerability(
        self,
        name: str,
        description: str,
        suggestion: str,
        evidence: List[str],
    ) -> Dict:
        """创建漏洞结构"""
        return {
            "rule_id": self.RULE_ID,
            "name": name,
            "severity": self.SEVERITY,
            "score_deduction": self.SCORE_DEDUCTION,
            "description": description,
            "suggestion": suggestion,
            "evidence": evidence,
        }

    def send_request(
        self,
        url: str,
        payload: str,
        headers: Dict,
        timeout: int = 10,
    ) -> tuple:
        """发送 HTTP 请求"""
        method = self._request_format.get("method", "POST")
        param_name = self._request_format.get("param_name", "query")
        body = {param_name: payload}

        try:
            response = requests.request(
                method,
                url,
                json=body,
                headers=headers,
                timeout=timeout,
            )
            return response.status_code, response.text
        except Exception as e:
            return None, str(e)