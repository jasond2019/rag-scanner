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