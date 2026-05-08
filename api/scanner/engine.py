"""
Simplified Scan Engine for Vercel Serverless
Executes quick security checks without async/threading
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .detectors import PromptInjectionDetector, DataLeakDetector, AuthBypassDetector
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
    """简化版扫描引擎"""

    def __init__(self):
        self.scorer = VulnerabilityScorer()
        self.detectors = {
            "prompt_injection": PromptInjectionDetector(),
            "data_leak": DataLeakDetector(),
            "auth_bypass": AuthBypassDetector(),
        }

    def scan(
        self,
        task_id: str,
        target_url: str,
        headers: Dict,
        param_name: str = "query",
    ) -> ScanResult:
        """
        执行快速扫描

        Args:
            task_id: 任务 ID
            target_url: 目标 URL
            headers: 请求头（含认证）
            param_name: 参数名

        Returns:
            ScanResult: 扫描结果
        """
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