"""
触发词模块

提供增强的触发词管理和变体生成能力
用于提升 RAG Scanner 的检测覆盖率

主要功能：
- TriggerManager: 触发词管理器，加载和管理触发词库
- VariantGenerator: 变体生成器，自动生成攻击变体
"""

from .manager import TriggerManager, trigger_manager
from .variant_generator import VariantGenerator, variant_generator

__all__ = [
    "TriggerManager",
    "trigger_manager",
    "VariantGenerator",
    "variant_generator",
]