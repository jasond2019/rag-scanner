"""
Simplified Scan Engine for Vercel Serverless
使用 ragshield-rules 规则库
"""

from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime

from .detectors import (
    PromptInjectionDetector,
    JailbreakDetector,
    PrivacyDetector,
    SensitiveDetector,
    AuthBypassDetector,
    DataLeakDetector,
)
from .scorer import VulnerabilityScorer


@dataclass
class ScanResult:
    """扫描结果"""
    task_id: str
    status: str
    score: int = 100
    level: str = "low"
    vulnerabilities: List[Dict] = field(default_factory=list)
    score_breakdown: Dict = field(default_factory=dict)
    completed_at: str = ""


class ScanEngine:
    """扫描引擎"""

    def __init__(self):
        self.scorer = VulnerabilityScorer()
        # 6 个检测器
        self.detectors = {
            "prompt_injection": PromptInjectionDetector(max_payloads=30),
            "jailbreak": JailbreakDetector(max_payloads=20),
            "privacy": PrivacyDetector(),
            "sensitive": SensitiveDetector(),
            "auth_bypass": AuthBypassDetector(),
            "data_leak": DataLeakDetector(),
        }

    def scan(
        self,
        task_id: str,
        target_url: str,
        headers: Dict,
        param_name: str = "query",
    ) -> ScanResult:
        """执行扫描"""
        all_vulnerabilities = []

        # 设置请求格式
        for detector in self.detectors.values():
            detector.set_request_format({
                "method": "POST",
                "param_name": param_name,
                "headers": headers,
            })

        # 执行检测
        for detector_name, detector in self.detectors.items():
            try:
                vulns = detector.detect(target_url, headers, task_id)
                all_vulnerabilities.extend(vulns)
            except Exception as e:
                print(f"[{detector_name}] Error: {e}")

        # 计算评分
        score_breakdown = self.scorer.calculate_breakdown(all_vulnerabilities)
        score = score_breakdown["final_score"]
        level = self.scorer.get_risk_level(score)

        return ScanResult(
            task_id=task_id,
            status="completed",
            score=score,
            level=level,
            vulnerabilities=all_vulnerabilities,
            score_breakdown=score_breakdown,
            completed_at=datetime.utcnow().isoformat(),
        )