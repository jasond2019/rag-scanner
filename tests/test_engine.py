"""
Scan Engine Tests
"""

import pytest
import sys
import os

# 添加 api 目录到 Python 路径
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, api_dir)

from scanner.engine import ScanEngine
from scanner.scorer import VulnerabilityScorer


class TestScanEngine:
    """扫描引擎测试"""

    def setup_method(self):
        """每个测试方法前初始化"""
        self.engine = ScanEngine()

    def test_init_engine(self):
        """测试引擎初始化"""
        assert self.engine is not None

    def test_detectors_loaded(self):
        """测试检测器加载"""
        assert len(self.engine.detectors) == 10
        # 高危检测器
        assert "prompt_injection" in self.engine.detectors
        assert "data_leak" in self.engine.detectors
        assert "vector_injection" in self.engine.detectors
        assert "retrieval_pollution" in self.engine.detectors
        assert "model_jailbreak" in self.engine.detectors
        # 中危检测器
        assert "auth_bypass" in self.engine.detectors
        assert "api_abuse" in self.engine.detectors
        assert "log_leak" in self.engine.detectors
        # 低危检测器
        assert "dependency_check" in self.engine.detectors
        assert "config_check" in self.engine.detectors

    def test_scorer_initialized(self):
        """测试评分器初始化"""
        assert self.engine.scorer is not None
        assert isinstance(self.engine.scorer, VulnerabilityScorer)

    def test_set_request_format(self):
        """测试请求格式设置"""
        format_config = {
            "method": "POST",
            "param_name": "prompt",
            "headers": {"Authorization": "Bearer test"},
        }

        for detector in self.engine.detectors.values():
            detector.set_request_format(format_config)
            assert detector._request_format["param_name"] == "prompt"


class TestScanResult:
    """扫描结果测试"""

    def test_scan_result_structure(self):
        """测试扫描结果结构"""
        # 模拟扫描结果
        from scanner.engine import ScanResult

        result = ScanResult(
            task_id="test_001",
            target_type="url",
            target_value="https://example.com",
            step=1,
            status="completed",
            score=95,
            level="low",
            vulnerabilities=[],
            score_breakdown={"final_score": 95},
        )

        assert result.task_id == "test_001"
        assert result.target_type == "url"
        assert result.status == "completed"
        assert result.score == 95
        assert result.level == "low"
        assert len(result.vulnerabilities) == 0