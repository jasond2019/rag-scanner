"""
Rules Loader for Vercel Serverless
从 api/scanner/rules/ 加载规则库
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Rule:
    """规则数据结构"""
    rule_id: str
    rule_name: str
    rule_type: str = "keyword"
    level: str = "medium"
    patterns: List[str] = field(default_factory=list)
    action: str = "warn"
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


class RuleMatcher:
    """规则匹配引擎"""

    def __init__(self, rules: List[Rule]):
        self.rules = rules
        self._compiled_patterns = []
        self._compile_patterns()

    def _compile_patterns(self):
        """预编译模式"""
        self._compiled_patterns = []
        for rule in self.rules:
            for pattern in rule.patterns:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    self._compiled_patterns.append((rule, compiled, pattern, True))
                except re.error:
                    self._compiled_patterns.append((rule, None, pattern.lower(), False))

    def match(self, text: str) -> List[Tuple[Rule, str]]:
        """匹配文本"""
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
        """去重"""
        seen = set()
        result = []
        for rule, pattern in matches:
            if rule.rule_id not in seen:
                seen.add(rule.rule_id)
                result.append((rule, pattern))
        return result


class RulesLoader:
    """规则加载器"""

    def __init__(self, rules_dir: Optional[str] = None):
        if rules_dir is None:
            # Vercel: 从 api/scanner/rules/ 加载
            self.rules_dir = Path(__file__).parent / "rules"
        else:
            self.rules_dir = Path(rules_dir)

    def load_category(self, category: str) -> List[Rule]:
        """加载指定类别规则"""
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
                        rule_id=r.get("rule_id", ""),
                        rule_name=r.get("rule_name", ""),
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
                print(f"[Warning] Failed to load {file}: {e}")

        return rules

    def load_all_patterns(self, category: str) -> List[str]:
        """加载所有模式"""
        patterns = []
        for rule in self.load_category(category):
            patterns.extend(rule.patterns)
        return patterns

    def load_sensitive_words(self) -> List[str]:
        """加载敏感词"""
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
                print(f"[Warning] Failed to load {file}: {e}")

        return list(set(words))

    def load_privacy_rules(self) -> List[PrivacyRule]:
        """加载隐私规则"""
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
                        rule_id=r.get("rule_id", ""),
                        rule_name=r.get("rule_name", ""),
                        pattern=r.get("pattern", ""),
                        level=r.get("level", "high"),
                        action=r.get("action", "mask"),
                    ))
            except Exception as e:
                print(f"[Warning] Failed to load {file}: {e}")

        return rules

    def get_stats(self) -> Dict:
        """统计信息"""
        return {
            "injection_rules": len(self.load_category("injection")),
            "injection_patterns": len(self.load_all_patterns("injection")),
            "jailbreak_rules": len(self.load_category("jailbreak")),
            "jailbreak_patterns": len(self.load_all_patterns("jailbreak")),
            "sensitive_words": len(self.load_sensitive_words()),
            "privacy_rules": len(self.load_privacy_rules()),
        }