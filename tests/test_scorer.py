"""
评分系统单元测试
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "api"))

from scanner.scorer import VulnerabilityScorer


class TestVulnerabilityScorer:
    """评分器测试"""
    
    def setup_method(self):
        self.scorer = VulnerabilityScorer()
    
    def test_calculate_breakdown_no_vulns(self):
        """测试无漏洞时的评分"""
        result = self.scorer.calculate_breakdown([])
        assert result["base_score"] == 100
        assert result["final_score"] == 100
        assert result["total_deduction"] == 0
    
    def test_calculate_breakdown_critical(self):
        """测试高危漏洞扣分"""
        vulns = [
            {"severity": "critical"},
            {"severity": "critical"},
        ]
        result = self.scorer.calculate_breakdown(vulns)
        assert result["critical_count"] == 2
        assert result["critical_deduction"] == 30  # 2 * 15
        assert result["final_score"] == 70
    
    def test_calculate_breakdown_high(self):
        """测试中危漏洞扣分"""
        vulns = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "high"},
        ]
        result = self.scorer.calculate_breakdown(vulns)
        assert result["high_count"] == 3
        assert result["high_deduction"] == 30  # 3 * 10
        assert result["final_score"] == 70
    
    def test_calculate_breakdown_medium(self):
        """测试低危漏洞扣分"""
        vulns = [
            {"severity": "medium"},
            {"severity": "medium"},
        ]
        result = self.scorer.calculate_breakdown(vulns)
        assert result["medium_count"] == 2
        assert result["medium_deduction"] == 10  # 2 * 5
        assert result["final_score"] == 90
    
    def test_calculate_breakdown_mixed(self):
        """测试混合漏洞扣分"""
        vulns = [
            {"severity": "critical"},  # -15
            {"severity": "critical"},  # -15
            {"severity": "high"},      # -10
            {"severity": "high"},      # -10
            {"severity": "high"},      # -10
            {"severity": "medium"},    # -5
        ]
        result = self.scorer.calculate_breakdown(vulns)
        assert result["final_score"] == 35  # 100 - 65
    
    def test_calculate_breakdown_floor(self):
        """测试分数不低于 0"""
        vulns = [{"severity": "critical"} for _ in range(20)]  # -300
        result = self.scorer.calculate_breakdown(vulns)
        assert result["final_score"] == 0  # 最低 0 分
    
    def test_get_risk_level_high(self):
        """测试高风险等级"""
        assert self.scorer.get_risk_level(50) == "high"
        assert self.scorer.get_risk_level(69) == "high"
    
    def test_get_risk_level_medium(self):
        """测试中等风险等级"""
        assert self.scorer.get_risk_level(70) == "medium"
        assert self.scorer.get_risk_level(89) == "medium"
    
    def test_get_risk_level_low(self):
        """测试低风险等级"""
        assert self.scorer.get_risk_level(90) == "low"
        assert self.scorer.get_risk_level(100) == "low"
    
    def test_get_risk_color(self):
        """测试风险颜色"""
        assert self.scorer.get_risk_color(50) == "red"
        assert self.scorer.get_risk_color(80) == "yellow"
        assert self.scorer.get_risk_color(95) == "green"
    
    def test_generate_summary(self):
        """测试总结生成"""
        breakdown = {
            "base_score": 100,
            "critical_count": 2,
            "high_count": 3,
            "medium_count": 1,
            "final_score": 35,
        }
        summary = self.scorer.generate_summary(breakdown)
        assert "35 分" in summary
        assert "高风险" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
