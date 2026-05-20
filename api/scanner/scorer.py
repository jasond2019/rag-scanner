"""
Vulnerability Scorer
Simplified version for Vercel Serverless
"""

from typing import Dict, List


class VulnerabilityScorer:
    """漏洞评分器"""

    SEVERITY_DEDUCTIONS = {
        "critical": 15,
        "high": 10,
        "medium": 5,
        "low": 2,
    }

    RISK_LEVELS = {
        "high": (0, 69),
        "medium": (70, 89),
        "low": (90, 100),
    }

    def calculate_breakdown(self, vulnerabilities: List[Dict]) -> Dict:
        """计算评分明细"""
        base_score = 100
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for vuln in vulnerabilities:
            severity = vuln.get("severity", "low")
            if severity in counts:
                counts[severity] += 1

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
        """根据分数获取风险等级"""
        for level, (min_score, max_score) in self.RISK_LEVELS.items():
            if min_score <= score <= max_score:
                return level
        return "high"

    def get_risk_color(self, score: int) -> str:
        """根据分数获取风险颜色"""
        level = self.get_risk_level(score)
        colors = {"high": "red", "medium": "yellow", "low": "green"}
        return colors.get(level, "red")

    def generate_summary(self, breakdown: Dict) -> str:
        """生成评分总结"""
        final_score = breakdown.get("final_score", 100)
        risk_level = self.get_risk_level(final_score)

        risk_names = {"high": "高风险", "medium": "中等风险", "low": "低风险"}

        critical = breakdown.get("critical_count", 0)
        high = breakdown.get("high_count", 0)
        medium = breakdown.get("medium_count", 0)

        return f"安全评分 {final_score} 分，风险等级：{risk_names[risk_level]}，发现 {critical + high + medium} 个漏洞"