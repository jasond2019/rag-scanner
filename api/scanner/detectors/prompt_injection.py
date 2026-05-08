"""
Prompt Injection Detector
使用 ragshield-rules 规则库 (286+ patterns)
"""

import re
from typing import Dict, List
from .base import BaseDetector
from ..rules_loader import RulesLoader


class PromptInjectionDetector(BaseDetector):
    """提示词注入检测器"""

    SEVERITY = "critical"
    SCORE_DEDUCTION = 15
    RULE_ID = "RAG-SEC-001"

    # 检测响应中的信号
    SIGNALS = [
        "system prompt", "system instruction", "configuration",
        "internal directive", "prompt template",
        "系统提示", "系统指令", "配置", "指令",
    ]

    def __init__(self, max_payloads: int = 30):
        """
        Args:
            max_payloads: 最大测试 payload 数量（避免 Vercel 超时）
        """
        super().__init__()
        loader = RulesLoader()
        # 加载规则库，限制数量避免超时
        self.payloads = loader.load_all_patterns("injection")[:max_payloads]
        self.rules = loader.load_category("injection")

    def detect(self, target_url: str, headers: Dict, task_id: str) -> List[Dict]:
        """执行检测"""
        vulnerabilities = []

        for payload in self.payloads:
            status, response = self.send_request(target_url, payload, headers)

            if status and response:
                for signal in self.SIGNALS:
                    if re.search(signal, response, re.IGNORECASE):
                        vulnerabilities.append(
                            self.create_vulnerability(
                                name="Prompt Injection Vulnerability",
                                description="API may leak system instructions when receiving crafted prompts",
                                suggestion="Implement input validation and output filtering",
                                evidence=[f"Payload: {payload[:60]}...", f"Signal: {signal}"],
                            )
                        )
                        break

        return self._deduplicate(vulnerabilities)

    def _deduplicate(self, vulns: List[Dict]) -> List[Dict]:
        """去重"""
        seen = set()
        result = []
        for v in vulns:
            key = v.get("evidence", [""])[0]
            if key not in seen:
                seen.add(key)
                result.append(v)
        return result