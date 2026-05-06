"""
加权计分引擎
评分规则（CEO 确认版）：
- 基础分：100 分
- 高危漏洞：-15 分/个
- 中危漏洞：-10 分/个
- 低危漏洞：-5 分/个
- 最低分：0 分
"""

from typing import Dict, List


class VulnerabilityScorer:
    """漏洞评分器"""
    
    # 漏洞等级扣分映射
    SEVERITY_DEDUCTIONS = {
        "critical": 15,  # 高危
        "high": 10,      # 中危
        "medium": 5,     # 低危
        "low": 2,        # 轻微
    }
    
    # 风险等级阈值
    RISK_LEVELS = {
        "high": (0, 69),      # 0-69: 高风险（红色）
        "medium": (70, 89),   # 70-89: 中等风险（黄色）
        "low": (90, 100),     # 90-100: 低风险（绿色）
    }
    
    def calculate_breakdown(self, vulnerabilities: List[Dict]) -> Dict:
        """
        计算评分明细
        
        Args:
            vulnerabilities: 漏洞列表
        
        Returns:
            Dict: 评分明细
                {
                    "base_score": 100,
                    "critical_count": 2,
                    "critical_deduction": 30,
                    "high_count": 3,
                    "high_deduction": 30,
                    "medium_count": 1,
                    "medium_deduction": 5,
                    "low_count": 0,
                    "low_deduction": 0,
                    "total_deduction": 65,
                    "final_score": 35
                }
        """
        base_score = 100
        
        # 统计各等级漏洞数量
        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "low")
            if severity in counts:
                counts[severity] += 1
        
        # 计算扣分
        deductions = {
            severity: count * self.SEVERITY_DEDUCTIONS.get(severity, 0)
            for severity, count in counts.items()
        }
        
        total_deduction = sum(deductions.values())
        final_score = max(0, base_score - total_deduction)
        
        return {
            "base_score": base_score,
            "critical_count": counts["critical"],
            "critical_deduction": deductions["critical"],
            "high_count": counts["high"],
            "high_deduction": deductions["high"],
            "medium_count": counts["medium"],
            "medium_deduction": deductions["medium"],
            "low_count": counts["low"],
            "low_deduction": deductions["low"],
            "total_deduction": total_deduction,
            "final_score": final_score,
        }
    
    def get_risk_level(self, score: int) -> str:
        """
        根据分数获取风险等级
        
        Args:
            score: 评分 (0-100)
        
        Returns:
            str: risk level (high, medium, low)
        """
        for level, (min_score, max_score) in self.RISK_LEVELS.items():
            if min_score <= score <= max_score:
                return level
        return "high"  # 默认高风险
    
    def get_risk_color(self, score: int) -> str:
        """
        获取风险等级对应的颜色
        
        Args:
            score: 评分 (0-100)
        
        Returns:
            str: 颜色 (red, yellow, green)
        """
        level = self.get_risk_level(score)
        color_map = {
            "high": "red",
            "medium": "yellow",
            "low": "green",
        }
        return color_map.get(level, "red")
    
    def generate_summary(self, score_breakdown: Dict) -> str:
        """
        生成评分总结
        
        Args:
            score_breakdown: 评分明细
        
        Returns:
            str: 总结文本
        """
        score = score_breakdown["final_score"]
        level = self.get_risk_level(score)
        
        level_text = {
            "high": "高风险",
            "medium": "中等风险",
            "low": "低风险",
        }
        
        summary = f"系统安全评分为 {score} 分（{level_text.get(level, '未知风险')}）。\n"
        
        if score_breakdown["critical_count"] > 0:
            summary += f"发现 {score_breakdown['critical_count']} 个高危漏洞，"
        if score_breakdown["high_count"] > 0:
            summary += f"{score_breakdown['high_count']} 个中危漏洞，"
        if score_breakdown["medium_count"] > 0:
            summary += f"{score_breakdown['medium_count']} 个低危漏洞。"
        
        if score < 70:
            summary += "\n⚠️ 建议立即修复高危漏洞，联系安全专家进行诊断。"
        elif score < 90:
            summary += "\nℹ️ 建议逐步修复发现的问题，提升系统安全性。"
        else:
            summary += "\n✅ 系统安全性良好，请继续保持。"
        
        return summary
