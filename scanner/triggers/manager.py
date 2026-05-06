"""
触发词管理器
负责加载和管理增强触发词库
"""

import json
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class TriggerConfig:
    """触发词配置"""
    version: str
    last_sync: str
    triggers: Dict[str, Dict]
    sources: List[str] = None


class TriggerManager:
    """触发词管理器 - 负责加载和管理触发词库"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._triggers: Dict[str, Set[str]] = {}
        self._patterns: Dict[str, List[str]] = {}
        self._detection_signals: Dict[str, List[str]] = {}
        self._config: Dict = {}
        
        # 加载配置
        self._load_config()
        
        print(f"[TriggerManager] 已加载 {len(self._triggers)} 个触发词类别")
        print(f"[TriggerManager] 触发词总数: {self.get_trigger_count()}")
    
    def _load_config(self):
        """加载触发词配置文件"""
        # 相对于当前文件路径
        config_path = Path(__file__).parent / "config.json"
        
        if not config_path.exists():
            print(f"[TriggerManager] 配置文件不存在: {config_path}")
            self._load_default_config()
            return
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            self._config = config
            
            # 解析触发词
            for category, data in config.get("triggers", {}).items():
                self._triggers[category] = set(data.get("keywords", []))
                self._patterns[category] = data.get("patterns", [])
                self._detection_signals[category] = data.get("detection_signals", [])
            
            version = config.get("version", "unknown")
            sources = config.get("sources", [])
            metadata = config.get("metadata", {})
            
            print(f"[TriggerManager] 加载配置: v{version}, 来源: {sources}")
            print(f"[TriggerManager] 触发词统计: {metadata}")
            
        except Exception as e:
            print(f"[TriggerManager] 加载配置失败: {e}")
            self._load_default_config()
    
    def _load_default_config(self):
        """加载默认配置（内置触发词）"""
        self._triggers = {
            "prompt_injection": {
                "忽略", "忘记", "system", "prompt", 
                "DAN", "developer mode", "ignore"
            },
            "sensitive_data": {
                "密码", "密钥", "api_key", "token", "secret"
            }
        }
        self._detection_signals = {
            "prompt_injection": ["系统", "指令", "prompt", "internal"],
            "sensitive_data": ["password", "key", "secret"]
        }
    
    def get_triggers(self, category: str) -> List[str]:
        """
        获取指定类别的触发词
        
        Args:
            category: 触发词类别
            
        Returns:
            触发词列表
        """
        return list(self._triggers.get(category, []))
    
    def get_all_triggers(self) -> Dict[str, List[str]]:
        """
        获取所有触发词
        
        Returns:
            按类别分组的触发词字典
        """
        return {k: list(v) for k, v in self._triggers.items()}
    
    def get_detection_signals(self, category: str) -> List[str]:
        """
        获取指定类别的检测信号
        
        Args:
            category: 触发词类别
            
        Returns:
            检测信号列表
        """
        return self._detection_signals.get(category, [])
    
    def get_all_detection_signals(self) -> Dict[str, List[str]]:
        """
        获取所有检测信号
        
        Returns:
            按类别分组的检测信号字典
        """
        return self._detection_signals.copy()
    
    def get_patterns(self, category: str) -> List[str]:
        """
        获取指定类别的正则模式
        
        Args:
            category: 触发词类别
            
        Returns:
            正则模式列表
        """
        return self._patterns.get(category, [])
    
    def search_trigger(self, text: str, category: str = None) -> List[str]:
        """
        搜索触发词
        
        Args:
            text: 待搜索文本
            category: 可选，指定类别
            
        Returns:
            匹配的触发词列表
        """
        text_lower = text.lower()
        matches = []
        
        categories = [category] if category else self._triggers.keys()
        
        for cat in categories:
            for trigger in self._triggers.get(cat, []):
                if trigger.lower() in text_lower:
                    matches.append(trigger)
        
        return matches
    
    def get_trigger_count(self) -> int:
        """获取总触发词数量"""
        return sum(len(v) for v in self._triggers.values())
    
    def get_config_info(self) -> Dict:
        """
        获取配置信息
        
        Returns:
            配置元信息
        """
        return {
            "version": self._config.get("version", "unknown"),
            "last_sync": self._config.get("last_sync", "unknown"),
            "sources": self._config.get("sources", []),
            "categories": list(self._triggers.keys()),
            "total_triggers": self.get_trigger_count()
        }


# 全局单例实例
trigger_manager = TriggerManager()