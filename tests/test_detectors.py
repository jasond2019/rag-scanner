"""
检测器单元测试
"""

import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "api"))

from scanner.detectors.base import BaseDetector
from scanner.detectors.data_leak import DataLeakDetector
from scanner.detectors.prompt_injection import PromptInjectionDetector
from scanner.detectors.jailbreak import JailbreakDetector


class TestDataLeakDetector:
    """数据泄露检测器测试"""

    def setup_method(self):
        self.detector = DataLeakDetector()

    def test_init(self):
        """测试初始化"""
        assert self.detector.SEVERITY == "critical"
        assert self.detector.SCORE_DEDUCTION == 15
        assert self.detector.RULE_ID == "RAG-SEC-002"

    def test_payloads_defined(self):
        """测试 payloads 定义"""
        assert len(self.detector.PAYLOADS) > 0

    def test_patterns_defined(self):
        """测试敏感模式定义"""
        assert len(self.detector.LEAK_PATTERNS) > 0

    def test_set_request_format(self):
        """测试请求格式设置"""
        format_config = {
            "method": "POST",
            "param_name": "prompt",
            "headers": {"Authorization": "Bearer test"},
        }
        self.detector.set_request_format(format_config)
        assert self.detector._request_format["param_name"] == "prompt"


class TestPromptInjectionDetector:
    """提示注入检测器测试"""

    def setup_method(self):
        self.detector = PromptInjectionDetector()

    def test_init(self):
        """测试初始化"""
        assert self.detector.SEVERITY == "critical"
        assert self.detector.SCORE_DEDUCTION == 15


class TestJailbreakDetector:
    """越狱检测器测试"""

    def setup_method(self):
        self.detector = JailbreakDetector()

    def test_init(self):
        """测试初始化"""
        assert self.detector.SEVERITY == "critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])