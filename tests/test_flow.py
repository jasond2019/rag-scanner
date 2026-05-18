"""
完整扫描流程测试
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加 api 目录到 Python 路径
api_dir = Path(__file__).parent.parent / "api"
sys.path.insert(0, str(api_dir))


class TestScanFlow:
    """完整扫描流程测试"""

    def test_flow_task_creation(self, test_db):
        """测试流程：任务创建"""
        if not test_db:
            pytest.skip("Database not available")

        from lib.db import ScanTask

        task_id = "test_flow_001"

        # 1. 创建任务
        task = ScanTask(
            id=task_id,
            target_type="url",
            target_value="https://example.com/api",
            status="queued",
            progress=0,
            current_step="waiting"
        )
        test_db.add(task)
        test_db.commit()

        # 2. 验证创建成功
        saved = test_db.query(ScanTask).filter(ScanTask.id == task_id).first()
        assert saved is not None
        assert saved.status == "queued"

        # 清理
        test_db.delete(saved)
        test_db.commit()

    def test_flow_progress_update(self, test_db):
        """测试流程：进度更新"""
        if not test_db:
            pytest.skip("Database not available")

        from lib.db import ScanTask

        task_id = "test_flow_progress"

        # 1. 创建任务
        task = ScanTask(
            id=task_id,
            target_type="url",
            target_value="https://example.com",
            status="queued",
            progress=0
        )
        test_db.add(task)
        test_db.commit()

        # 2. 模拟进度更新
        task.status = "running"
        task.progress = 25
        task.current_step = "提示词注入检测"
        test_db.commit()

        # 3. 验证进度更新
        updated = test_db.query(ScanTask).filter(ScanTask.id == task_id).first()
        assert updated.status == "running"
        assert updated.progress == 25

        # 清理
        test_db.delete(updated)
        test_db.commit()

    def test_flow_completion(self, test_db):
        """测试流程：任务完成"""
        if not test_db:
            pytest.skip("Database not available")

        from lib.db import ScanTask, Vulnerability
        import json

        task_id = "test_flow_complete"

        # 1. 创建任务
        task = ScanTask(
            id=task_id,
            target_type="url",
            target_value="https://example.com",
            status="running",
            progress=50
        )
        test_db.add(task)
        test_db.commit()

        # 2. 模拟完成
        task.status = "completed"
        task.progress = 100
        task.current_step = "扫描完成"
        task.score = 90
        task.level = "low"
        task.completed_at = datetime.utcnow()
        test_db.commit()

        # 3. 验证完成状态
        result = test_db.query(ScanTask).filter(ScanTask.id == task_id).first()
        assert result.status == "completed"
        assert result.score == 90
        assert result.level == "low"

        # 清理
        test_db.delete(result)
        test_db.commit()

    def test_flow_with_vulnerability(self, test_db):
        """测试流程：包含漏洞的结果"""
        if not test_db:
            pytest.skip("Database not available")

        from lib.db import ScanTask, Vulnerability
        import json

        task_id = "test_flow_vuln"

        # 1. 创建任务
        task = ScanTask(
            id=task_id,
            target_type="url",
            target_value="https://vulnerable-app.com",
            status="completed",
            progress=100,
            score=70,
            level="medium"
        )
        test_db.add(task)
        test_db.commit()

        # 2. 添加漏洞
        vuln1 = Vulnerability(
            id=f"{task_id}_vuln_001",
            task_id=task_id,
            rule_id="prompt_injection",
            name="提示词注入",
            severity="high",
            score_deduction=10,
            description="检测到注入风险",
            suggestion="加强过滤"
        )
        vuln2 = Vulnerability(
            id=f"{task_id}_vuln_002",
            task_id=task_id,
            rule_id="data_leak",
            name="数据泄露",
            severity="medium",
            score_deduction=5,
            description="敏感数据暴露"
        )
        test_db.add(vuln1)
        test_db.add(vuln2)
        test_db.commit()

        # 3. 验证漏洞统计
        vuln_count = test_db.query(Vulnerability).filter(
            Vulnerability.task_id == task_id
        ).count()
        assert vuln_count == 2

        # 清理
        test_db.query(Vulnerability).filter(Vulnerability.task_id == task_id).delete()
        test_db.query(ScanTask).filter(ScanTask.id == task_id).delete()
        test_db.commit()

    def test_flow_error_handling(self, test_db):
        """测试流程：错误处理"""
        if not test_db:
            pytest.skip("Database not available")

        from lib.db import ScanTask

        task_id = "test_flow_error"

        # 1. 创建任务
        task = ScanTask(
            id=task_id,
            target_type="url",
            target_value="https://invalid-url",
            status="running",
            progress=30
        )
        test_db.add(task)
        test_db.commit()

        # 2. 模拟失败
        task.status = "failed"
        task.progress = 0
        task.current_step = "扫描失败"
        test_db.commit()

        # 3. 验证失败状态
        failed = test_db.query(ScanTask).filter(ScanTask.id == task_id).first()
        assert failed.status == "failed"

        # 清理
        test_db.delete(failed)
        test_db.commit()


class TestScoringFlow:
    """评分流程测试"""

    def test_score_calculation(self):
        """测试评分计算流程"""
        from scanner.scorer import VulnerabilityScorer

        scorer = VulnerabilityScorer()

        # 模拟漏洞列表
        vulns = [
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
        ]

        result = scorer.calculate_breakdown(vulns)

        # 验证评分逻辑
        assert result["final_score"] == 100 - 10 - 5 - 2  # 83
        assert result["high_count"] == 1
        assert result["medium_count"] == 1
        assert result["low_count"] == 1

        # 验证风险等级
        level = scorer.get_risk_level(result["final_score"])
        assert level == "medium"  # 83 在 70-89 范围

    def test_empty_vulns_score(self):
        """测试无漏洞评分"""
        from scanner.scorer import VulnerabilityScorer

        scorer = VulnerabilityScorer()
        result = scorer.calculate_breakdown([])

        assert result["final_score"] == 100
        level = scorer.get_risk_level(100)
        assert level == "low"


class TestDetectorFlow:
    """检测器流程测试"""

    def test_detector_init(self):
        """测试检测器初始化流程"""
        from scanner.detectors import (
            PromptInjectionDetector,
            ModelJailbreakDetector,
            DataLeakDetector,
        )
        from scanner.rate_limiter import RateLimiter
        from scanner.auditor import ScanAuditor

        # 创建依赖对象
        rate_limiter = RateLimiter()
        auditor = ScanAuditor()

        # 初始化检测器
        injection_detector = PromptInjectionDetector(rate_limiter, auditor)
        jailbreak_detector = ModelJailbreakDetector(rate_limiter, auditor)
        data_leak_detector = DataLeakDetector(rate_limiter, auditor)

        # 验证属性（根据实际实现）
        assert injection_detector.SEVERITY == "critical"
        assert jailbreak_detector.SEVERITY == "high"  # ModelJailbreak 是 high
        assert data_leak_detector.SEVERITY == "critical"

    def test_request_format_setting(self):
        """测试请求格式设置流程"""
        from scanner.detectors import PromptInjectionDetector
        from scanner.rate_limiter import RateLimiter
        from scanner.auditor import ScanAuditor

        rate_limiter = RateLimiter()
        auditor = ScanAuditor()
        detector = PromptInjectionDetector(rate_limiter, auditor)

        # 设置请求格式
        format_config = {
            "method": "POST",
            "param_name": "prompt",
            "headers": {"Authorization": "Bearer test"},
        }
        detector.set_request_format(format_config)

        # 验证设置生效
        assert detector._request_format["param_name"] == "prompt"