"""
检测器单元测试
"""

import pytest
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.detectors.config_check import ConfigCheckDetector
from scanner.detectors.data_leak import DataLeakDetector


class MockAuditor:
    """模拟审计器"""
    async def log_request(self, **kwargs):
        pass
    
    async def log_error(self, **kwargs):
        pass


class MockRateLimiter:
    """模拟速率限制器"""
    async def acquire(self, target):
        return True


class TestConfigCheckDetector:
    """配置检测器测试"""
    
    def setup_method(self):
        self.detector = ConfigCheckDetector(MockAuditor())
    
    @pytest.mark.asyncio
    async def test_detect_default_password(self):
        """测试默认密码检测"""
        config = {
            "requirements": "flask==2.0",
            "password": "admin123"
        }
        vulns = await self.detector.detect_config(config)
        assert len(vulns) > 0
        assert any(v["rule_id"] == "RAG-SEC-010" for v in vulns)

    @pytest.mark.asyncio
    async def test_detect_hardcoded_key(self):
        """测试硬编码密钥检测"""
        config = {
            "api_key": "abcdefghijklmnopqrst"  # 20 chars, pure alphanumeric
        }
        vulns = await self.detector.detect_config(config)
        assert len(vulns) > 0
    
    @pytest.mark.asyncio
    async def test_detect_debug_mode(self):
        """测试调试模式检测"""
        config = {
            "debug": True,
            "DEBUG": "True"
        }
        vulns = await self.detector.detect_config(config)
        assert len(vulns) > 0
    
    @pytest.mark.asyncio
    async def test_no_vulns(self):
        """测试无漏洞配置"""
        config = {
            "name": "safe-app",
            "version": "1.0.0"
        }
        vulns = await self.detector.detect_config(config)
        assert len(vulns) == 0


class TestDataLeakDetector:
    """数据泄露检测器测试"""
    
    def setup_method(self):
        self.detector = DataLeakDetector(MockRateLimiter(), MockAuditor())
    
    def test_init(self):
        """测试初始化"""
        assert len(self.detector.SENSITIVE_PATHS) > 0
        assert self.detector.SEVERITY == "critical"
        assert self.detector.SCORE_DEDUCTION == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
