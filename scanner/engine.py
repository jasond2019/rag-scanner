"""
扫描引擎主入口
负责协调 10 个检测器的执行
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .detectors import (
    PromptInjectionDetector,
    DataLeakDetector,
    VectorInjectionDetector,
    RetrievalPollutionDetector,
    AuthBypassDetector,
    APIAbuseDetector,
    LogLeakDetector,
    ModelJailbreakDetector,
    DependencyCheckDetector,
    ConfigCheckDetector,
)
from .scorer import VulnerabilityScorer
from .rate_limiter import RateLimiter
from .auditor import ScanAuditor
from .format_detector import APIFormatDetector  # 新增


@dataclass
class ScanResult:
    """扫描结果数据结构"""
    task_id: str
    target_type: str
    target_value: str
    step: int
    status: str  # queued, running, completed, failed
    score: Optional[int] = None
    level: Optional[str] = None  # high, medium, low
    vulnerabilities: List[Dict] = None
    score_breakdown: Optional[Dict] = None
    audit_logs: List[Dict] = None  # 审计日志
    created_at: str = None
    completed_at: str = None
    
    def __post_init__(self):
        if self.vulnerabilities is None:
            self.vulnerabilities = []
        if self.audit_logs is None:
            self.audit_logs = []
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class ScanEngine:
    """扫描引擎主类"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.rate_limiter = RateLimiter(max_requests_per_second=10)
        self.auditor = ScanAuditor()
        self.scorer = VulnerabilityScorer()

        # 新增：API 格式探测器
        self.format_detector = APIFormatDetector()

        # 初始化 10 个检测器
        self.detectors = {
            "prompt_injection": PromptInjectionDetector(self.rate_limiter, self.auditor),
            "data_leak": DataLeakDetector(self.rate_limiter, self.auditor),
            "vector_injection": VectorInjectionDetector(self.rate_limiter, self.auditor),
            "retrieval_pollution": RetrievalPollutionDetector(self.rate_limiter, self.auditor),
            "auth_bypass": AuthBypassDetector(self.rate_limiter, self.auditor),
            "api_abuse": APIAbuseDetector(self.rate_limiter, self.auditor),
            "log_leak": LogLeakDetector(self.rate_limiter, self.auditor),
            "model_jailbreak": ModelJailbreakDetector(self.rate_limiter, self.auditor),
            "dependency_check": DependencyCheckDetector(self.auditor),
            "config_check": ConfigCheckDetector(self.auditor),
        }
        
        # 检测器优先级（高危优先）
        self.detector_order = [
            "prompt_injection",      # -15
            "data_leak",             # -15
            "vector_injection",      # -15
            "retrieval_pollution",   # -15
            "auth_bypass",           # -10
            "api_abuse",             # -10
            "log_leak",              # -10
            "model_jailbreak",       # -10
            "dependency_check",      # -5
            "config_check",          # -5
        ]
    
    async def scan(self, task_id: str, target_type: str, target_value: str,
                   curl_data: Optional[Dict] = None,  # 新增：curl 解析数据
                   step: int = 1, config_data: Optional[Dict] = None,
                   progress_callback: Optional[callable] = None) -> ScanResult:
        """
        执行扫描任务

        Args:
            task_id: 任务 ID
            target_type: url, endpoint, config
            target_value: 目标 URL 或配置内容
            curl_data: curl 解析后的请求格式（如果用户提供 curl 命令）
            step: 1=初步扫描，2=配置补充
            config_data: 配置文件内容（step=2 时使用）
            progress_callback: 进度回调函数 (progress: int, current_step: str)

        Returns:
            ScanResult: 扫描结果
        """
        result = ScanResult(
            task_id=task_id,
            target_type=target_type,
            target_value=target_value,
            step=step,
            status="running"
        )

        all_vulnerabilities = []
        total_detectors = len(self.detector_order)
        completed = 0

        try:
            # === Phase 0: API 格式探测（新增） ===
            request_format = None
            target_url = target_value

            if curl_data:
                # 使用 curl 解析的格式
                request_format = self.format_detector.get_request_format(curl_data)
                target_url = curl_data.get("url", target_value)

                if progress_callback:
                    await progress_callback(2, f"format: curl ({request_format['param_name']})")
            else:
                # 使用自动探测
                if progress_callback:
                    await progress_callback(0, "format_detection")

                detection_result = await self.format_detector.detect(target_value)
                request_format = self.format_detector.get_request_format(detection_result)
                target_url = detection_result.get("url", target_value)

                if progress_callback:
                    param = request_format.get("param_name", "query")
                    confidence = detection_result.get("confidence", 0.5)
                    await progress_callback(5, f"format_detected: {param} ({confidence:.0%})")

            # 为所有检测器设置请求格式
            for detector_name, detector in self.detectors.items():
                detector.set_request_format(request_format)

            # === Phase 1: 执行在线检测 ===
            if step == 1:
                for detector_name in self.detector_order:
                    detector = self.detectors[detector_name]

                    # 更新进度
                    completed += 1
                    progress = int(5 + (completed / total_detectors) * 95)
                    if progress_callback:
                        await progress_callback(progress, detector_name)

                    # 执行检测（传递 task_id）
                    try:
                        vulns = await detector.detect(target_type, target_url, task_id)
                        all_vulnerabilities.extend(vulns)
                    except Exception as e:
                        # 记录检测器错误，继续执行其他检测
                        await self.auditor.log_error(task_id, detector_name, str(e))
            
            # Step 2: 配置文件分析
            elif step == 2 and config_data:
                # 只执行配置相关的检测
                config_detectors = ["dependency_check", "config_check"]
                for detector_name in config_detectors:
                    detector = self.detectors[detector_name]
                    
                    completed += 1
                    progress = int((completed / len(config_detectors)) * 100) if len(config_detectors) > 0 else 100
                    if progress_callback:
                        await progress_callback(progress, detector_name)
                    
                    try:
                        vulns = await detector.detect_config(config_data, task_id)
                        all_vulnerabilities.extend(vulns)
                    except Exception as e:
                        await self.auditor.log_error(task_id, detector_name, str(e))
            
            # 计算评分
            result.vulnerabilities = all_vulnerabilities
            result.score_breakdown = self.scorer.calculate_breakdown(all_vulnerabilities)
            result.score = result.score_breakdown["final_score"]
            result.level = self.scorer.get_risk_level(result.score)
            result.status = "completed"
            
        except Exception as e:
            result.status = "failed"
            await self.auditor.log_error(task_id, "engine", str(e))
        
        # 获取审计日志
        result.audit_logs = self.auditor.get_audit_log(task_id)
        result.completed_at = datetime.utcnow().isoformat()
        return result

    async def merge_results(self, step1_result: ScanResult, 
                           step2_result: ScanResult) -> ScanResult:
        """
        合并两次扫描结果
        
        Args:
            step1_result: Step 1 扫描结果
            step2_result: Step 2 扫描结果
        
        Returns:
            ScanResult: 合并后的结果
        """
        # 合并漏洞列表（去重）
        all_vulns = step1_result.vulnerabilities.copy()
        seen_ids = {v["id"] for v in all_vulns}
        
        for vuln in step2_result.vulnerabilities:
            if vuln["id"] not in seen_ids:
                all_vulns.append(vuln)
                seen_ids.add(vuln["id"])
        
        # 重新计算评分
        merged = ScanResult(
            task_id=f"{step1_result.task_id}_merged",
            target_type=step1_result.target_type,
            target_value=step1_result.target_value,
            step=3,  # 合并后的步骤
            status="completed",
            vulnerabilities=all_vulns,
            created_at=step1_result.created_at,
            completed_at=datetime.utcnow().isoformat()
        )
        
        merged.score_breakdown = self.scorer.calculate_breakdown(all_vulns)
        merged.score = merged.score_breakdown["final_score"]
        merged.level = self.scorer.get_risk_level(merged.score)
        
        return merged