"""
自动变体生成器
用于生成触发词的变体，增加检测覆盖率

支持的变体策略：
- synonym: 同义词替换
- pinyin: 拼音替换
- spacing: 空格干扰
- case: 大小写变形
- encoding: 编码变形
- char_swap: 字符替换
"""

import random
import re
from typing import List, Set


class VariantGenerator:
    """自动变体生成器"""
    
    # 同义词词典
    SYNONYMS = {
        "绕过": ["跳过", "突破", "无视", "突破"],
        "登录": ["登录", "认证", "授权", "验证", "登陆"],
        "密码": ["密码", "密钥", "口令", "pass", "password"],
        "获取": ["获取", "拿到", "得到", "取得"],
        "忽略": ["忽略", "无视", "跳过", "不管", "别管"],
        "忘记": ["忘记", "忘了", "忽略", "不管"],
        "系统": ["系统", "system", "系统", "系统"],
        "指令": ["指令", "命令", "指示", "instructions"],
        "输出": ["输出", "显示", "展示", "给出", "告诉"],
        "显示": ["显示", "输出", "展示", "给出"],
    }
    
    # 拼音映射
    PINYIN_MAP = {
        "密码": "mima",
        "登录": "denglu",
        "绕过": "raoguo",
        "系统": "xitong",
        "指令": "zhiling",
        "获取": "huoqu",
        "显示": "xianshi",
    }
    
    def __init__(self, enable_variants: bool = True):
        """
        初始化变体生成器
        
        Args:
            enable_variants: 是否启用变体生成
        """
        self.enable_variants = enable_variants
        self.strategies = [
            "synonym",      # 同义词替换
            "pinyin",       # 拼音替换
            "spacing",      # 空格干扰
            "case",         # 大小写
            "encoding",     # 编码变形
            "char_swap",    # 字符替换
        ]
    
    def generate(self, text: str, count: int = 3) -> List[str]:
        """
        生成变体
        
        Args:
            text: 原始文本
            count: 生成数量
            
        Returns:
            变体列表
        """
        if not self.enable_variants:
            return [text]
        
        if not text or not text.strip():
            return [text]
        
        variants: Set[str] = set()
        variants.add(text)  # 保留原始
        
        # 尝试生成变体
        attempts = 0
        max_attempts = count * 5
        
        while len(variants) < count and attempts < max_attempts:
            attempts += 1
            variant = self._apply_strategies(text)
            if variant and variant != text and variant.strip():
                variants.add(variant)
        
        # 转为列表，去重
        result = list(variants)[:count]
        
        # 确保原始文本在结果中
        if text not in result:
            result[0] = text
        
        return result
    
    def _apply_strategies(self, text: str) -> str:
        """随机应用 1-2 个策略"""
        num_strategies = random.randint(1, 2)
        selected = random.sample(self.strategies, min(num_strategies, len(self.strategies)))
        
        result = text
        for strategy in selected:
            result = self._apply_strategy(result, strategy)
        
        return result
    
    def _apply_strategy(self, text: str, strategy: str) -> str:
        """应用单个策略"""
        if strategy == "synonym":
            return self._synonym_replace(text)
        elif strategy == "pinyin":
            return self._pinyin_replace(text)
        elif strategy == "spacing":
            return self._spacing_distort(text)
        elif strategy == "case":
            return self._case_distort(text)
        elif strategy == "encoding":
            return self._encoding_distort(text)
        elif strategy == "char_swap":
            return self._char_swap(text)
        return text
    
    def _synonym_replace(self, text: str) -> str:
        """同义词替换"""
        result = text
        for word, synonyms in self.SYNONYMS.items():
            if word in result:
                # 随机选择同义词
                replacement = random.choice(synonyms)
                result = result.replace(word, replacement, 1)
        return result
    
    def _pinyin_replace(self, text: str) -> str:
        """拼音替换"""
        if random.random() > 0.4:  # 只有40%概率触发
            return text
        
        result = text
        for word, pinyin in self.PINYIN_MAP.items():
            if word in result:
                result = result.replace(word, pinyin, 1)
        return result
    
    def _spacing_distort(self, text: str) -> str:
        """空格干扰"""
        mode = random.choice(["zero", "random", "wrap"])
        
        if mode == "zero":
            # 零宽空格
            chars = []
            for c in text:
                if random.random() > 0.3:
                    chars.append(c + '\u200b')
                else:
                    chars.append(c)
            return ''.join(chars)
        elif mode == "random":
            # 随机空格
            chars = list(text)
            for i in range(len(chars)):
                if random.random() > 0.7:
                    chars[i] = chars[i] + ' '
            return ''.join(chars)
        else:
            # 首尾包裹
            return f' {text} '
    
    def _case_distort(self, text: str) -> str:
        """大小写变形"""
        # 随机选择变形方式
        choice = random.random()
        
        if choice < 0.33:
            return text.lower()
        elif choice < 0.66:
            return text.upper()
        else:
            # 首字母大写
            return text.title()
    
    def _encoding_distort(self, text: str) -> str:
        """编码变形"""
        if random.random() > 0.7:
            # Unicode 全角
            result = []
            for c in text:
                code = ord(c)
                if 0x21 <= code <= 0x7E:
                    result.append(chr(code + 0xFEE0))
                else:
                    result.append(c)
            return ''.join(result)
        return text
    
    def _char_swap(self, text: str) -> str:
        """字符替换（Leet Speak）"""
        replacements = {
            'a': '@', 'A': '4',
            'e': '3', 'E': '3',
            'i': '1', 'I': '1',
            'o': '0', 'O': '0',
            's': '$', 'S': '5',
            'l': '1',
        }
        
        result = list(text)
        replaced = False
        for i in range(len(result)):
            if result[i] in replacements and random.random() > 0.5:
                result[i] = replacements[result[i]]
                replaced = True
        
        # 只有真正发生了替换才返回变形后的结果
        return ''.join(result) if replaced else text
    
    def generate_batch(self, triggers: List[str], count_per: int = 2) -> List[str]:
        """
        批量生成变体
        
        Args:
            triggers: 触发词列表
            count_per: 每个触发词生成的变体数
            
        Returns:
            所有变体的列表
        """
        all_variants = []
        
        for trigger in triggers:
            variants = self.generate(trigger, count_per)
            all_variants.extend(variants)
        
        # 去重，保持顺序
        seen = set()
        result = []
        for v in all_variants:
            if v not in seen:
                seen.add(v)
                result.append(v)
        
        return result
    
    def get_enabled_strategies(self) -> List[str]:
        """获取启用的策略列表"""
        return self.strategies.copy()
    
    def set_enabled_strategies(self, strategies: List[str]):
        """
        设置启用的策略
        
        Args:
            strategies: 策略列表
        """
        self.strategies = strategies


# 全局生成器实例
variant_generator = VariantGenerator(enable_variants=True)