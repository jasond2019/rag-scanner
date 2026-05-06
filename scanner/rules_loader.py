"""
统一规则加载器
支持 RAG Scanner 和 RAGuard SDK 使用
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Rule:
    """规则数据结构"""
    rule_id: str
    rule_name: str
    rule_type: str = "keyword"  # keyword | pattern | semantic
    level: str = "medium"       # critical | high | medium | low
    patterns: List[str] = field(default_factory=list)
    action: str = "warn"        # block | warn | log | mask
    confidence_weight: float = 1.0
    tags: List[str] = field(default_factory=list)
    lang: str = "multi"
    source: str = ""
    suggestion: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.patterns is None:
            self.patterns = []


@dataclass
class PrivacyRule:
    """隐私正则规则"""
    rule_id: str
    rule_name: str
    pattern: str
    level: str = "high"
    action: str = "mask"
    mask_char: str = "*"
    mask_keep: int = 4
    test_cases: Dict = field(default_factory=dict)

    def __post_init__(self):
        if self.test_cases is None:
            self.test_cases = {}


class RuleMatcher:
    """规则匹配引擎"""

    def __init__(self, rules: List[Rule]):
        self.rules = rules
        self._compiled_patterns = []
        self._compile_patterns()

    def _compile_patterns(self):
        """预编译模式以提升性能"""
        self._compiled_patterns = []
        for rule in self.rules:
            for pattern in rule.patterns:
                # 尝试编译为正则
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    self._compiled_patterns.append((rule, compiled, pattern, True))
                except re.error:
                    # 非正则模式，使用字符串匹配
                    self._compiled_patterns.append((rule, None, pattern.lower(), False))

    def match(self, text: str) -> List[Tuple[Rule, str]]:
        """匹配文本中的规则"""
        matches = []
        text_lower = text.lower()

        for rule, compiled, pattern, is_regex in self._compiled_patterns:
            if is_regex:
                if compiled.search(text):
                    matches.append((rule, pattern))
            else:
                if pattern in text_lower:
                    matches.append((rule, pattern))

        return self._deduplicate(matches)

    def _deduplicate(self, matches: List[Tuple[Rule, str]]) -> List[Tuple[Rule, str]]:
        """按 rule_id 去重"""
        seen = set()
        result = []
        for rule, pattern in matches:
            if rule.rule_id not in seen:
                seen.add(rule.rule_id)
                result.append((rule, pattern))
        return result


class RulesLoader:
    """统一规则加载器"""

    def __init__(self, rules_dir: Optional[str] = None):
        if rules_dir is None:
            # 自动检测 submodule 路径
            rules_dir = self._detect_rules_dir()

        self.rules_dir = Path(rules_dir)

    def _detect_rules_dir(self) -> str:
        """自动检测规则目录位置（优先使用 ragshield-rules）"""
        current = Path(__file__).parent

        # 优先使用 ragshield-rules（共享规则库）
        possible_paths = [
            # ragshield-rules 在项目根目录
            current.parent.parent.parent / "ragshield-rules" / "rules",
            current.parent.parent / "ragshield-rules" / "rules",
            # workspace-ragshield 下的 ragshield-rules
            current.parent.parent.parent.parent / "ragshield-rules" / "rules",
            # 本地 rules 目录（备用）
            current / "rules",
            current.parent / "rules",
            current.parent.parent / "rules",
        ]

        for p in possible_paths:
            if p.exists() and p.is_dir():
                return str(p)

        # 默认使用本地 rules
        default = current / "rules"
        if not default.exists():
            raise FileNotFoundError(
                f"Rules directory not found. Searched: {[str(p) for p in possible_paths]}"
            )
        return str(default)

    def load_category(self, category: str) -> List[Rule]:
        """加载指定类别的所有规则"""
        rules = []
        category_dir = self.rules_dir / category

        if not category_dir.exists():
            return rules

        for file in category_dir.glob("*.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)

                for r in data.get("rules", []):
                    rules.append(Rule(
                        rule_id=r["rule_id"],
                        rule_name=r["rule_name"],
                        rule_type=r.get("rule_type", "keyword"),
                        level=r.get("level", "medium"),
                        patterns=r.get("patterns", []),
                        action=r.get("action", "warn"),
                        confidence_weight=r.get("confidence_weight", 1.0),
                        tags=r.get("tags", []),
                        lang=r.get("lang", "multi"),
                        source=r.get("source", ""),
                        suggestion=r.get("suggestion", ""),
                    ))
            except Exception as e:
                print(f"[Warning] 加载 {file} 失败: {e}")

        return rules

    def load_all_patterns(self, category: str) -> List[str]:
        """加载指定类别的所有模式字符串"""
        rules = self.load_category(category)
        patterns = []
        for rule in rules:
            patterns.extend(rule.patterns)
        return patterns

    def load_sensitive_words(self) -> List[str]:
        """加载所有敏感词"""
        words = []
        sensitive_dir = self.rules_dir / "sensitive"

        if not sensitive_dir.exists():
            return words

        for file in sensitive_dir.glob("*.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                words.extend(data.get("words", []))
            except Exception as e:
                print(f"[Warning] 加载 {file} 失败: {e}")

        return list(set(words))  # 去重

    def load_privacy_rules(self) -> List[PrivacyRule]:
        """加载隐私正则规则"""
        rules = []
        privacy_dir = self.rules_dir / "privacy"

        if not privacy_dir.exists():
            return rules

        for file in privacy_dir.glob("*.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)

                for r in data.get("rules", []):
                    rules.append(PrivacyRule(
                        rule_id=r["rule_id"],
                        rule_name=r["rule_name"],
                        pattern=r["pattern"],
                        level=r.get("level", "high"),
                        action=r.get("action", "mask"),
                        mask_char=r.get("mask_char", "*"),
                        mask_keep=r.get("mask_keep", 4),
                        test_cases=r.get("test_cases", {}),
                    ))
            except Exception as e:
                print(f"[Warning] 加载 {file} 失败: {e}")

        return rules

    def get_stats(self) -> Dict:
        """获取规则库统计信息"""
        return {
            "injection_rules": len(self.load_category("injection")),
            "injection_patterns": len(self.load_all_patterns("injection")),
            "jailbreak_rules": len(self.load_category("jailbreak")),
            "jailbreak_patterns": len(self.load_all_patterns("jailbreak")),
            "sensitive_words": len(self.load_sensitive_words()),
            "privacy_rules": len(self.load_privacy_rules()),
            "total_rules": (
                len(self.load_category("injection")) +
                len(self.load_category("jailbreak")) +
                len(self.load_privacy_rules())
            ),
        }


# 使用示例
if __name__ == "__main__":
    loader = RulesLoader()
    stats = loader.get_stats()

    print("规则库统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")