"""
文件操作标准模块
定义项目中文件操作的标准方法和最佳实践
"""

import os
import logging
from pathlib import Path
from typing import Optional, Union
from config.file_operations_config import (
    get_file_operation_params,
    validate_file_encoding,
    ensure_utf8_compliance,
    FILE_OPERATION_CONFIG
)


class SafeFileManager:
    """
    安全文件管理器
    提供标准化的文件操作方法，确保编码一致性
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def read_text_file(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        安全读取文本文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容，失败返回None
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.logger.error(f"文件不存在: {file_path}")
            return None
        
        try:
            # 验证文件编码
            is_valid, message = validate_file_encoding(str(file_path))
            if not is_valid:
                self.logger.warning(f"文件编码可能有问题: {file_path}, {message}")
            
            # 使用标准参数读取
            params = get_file_operation_params('r')
            with open(file_path, 'r', **params) as f:
                content = f.read()
            
            return content
            
        except Exception as e:
            self.logger.error(f"读取文件失败: {file_path}, 错误: {e}")
            return None
    
    def write_text_file(self, file_path: Union[str, Path], content: str, backup: bool = True) -> bool:
        """
        安全写入文本文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            backup: 是否备份原文件
            
        Returns:
            成功返回True，失败返回False
        """
        file_path = Path(file_path)
        
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 备份原文件（如果存在且启用备份）
            if backup and file_path.exists():
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                backup_path.write_bytes(file_path.read_bytes())
            
            # 确保内容符合UTF-8规范
            safe_content = ensure_utf8_compliance(content)
            
            # 使用标准参数写入
            params = get_file_operation_params('w')
            with open(file_path, 'w', **params) as f:
                f.write(safe_content)
            
            self.logger.info(f"成功写入文件: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"写入文件失败: {file_path}, 错误: {e}")
            return False
    
    def append_to_file(self, file_path: Union[str, Path], content: str) -> bool:
        """
        追加内容到文件
        
        Args:
            file_path: 文件路径
            content: 要追加的内容
            
        Returns:
            成功返回True，失败返回False
        """
        file_path = Path(file_path)
        
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 确保内容符合UTF-8规范
            safe_content = ensure_utf8_compliance(content)
            
            # 使用标准参数追加
            params = get_file_operation_params('a')
            with open(file_path, 'a', **params) as f:
                f.write(safe_content)
            
            self.logger.info(f"成功追加到文件: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"追加文件失败: {file_path}, 错误: {e}")
            return False
    
    def read_binary_file(self, file_path: Union[str, Path]) -> Optional[bytes]:
        """
        读取二进制文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容（bytes），失败返回None
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.logger.error(f"文件不存在: {file_path}")
            return None
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return content
            
        except Exception as e:
            self.logger.error(f"读取二进制文件失败: {file_path}, 错误: {e}")
            return None
    
    def write_binary_file(self, file_path: Union[str, Path], content: bytes) -> bool:
        """
        写入二进制文件
        
        Args:
            file_path: 文件路径
            content: 文件内容（bytes）
            
        Returns:
            成功返回True，失败返回False
        """
        file_path = Path(file_path)
        
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            self.logger.info(f"成功写入二进制文件: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"写入二进制文件失败: {file_path}, 错误: {e}")
            return False


# 全局文件管理器实例
safe_file_manager = SafeFileManager()


def read_file(file_path: Union[str, Path]) -> Optional[str]:
    """
    便捷函数：读取文本文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容，失败返回None
    """
    return safe_file_manager.read_text_file(file_path)


def write_file(file_path: Union[str, Path], content: str, backup: bool = True) -> bool:
    """
    便捷函数：写入文本文件
    
    Args:
        file_path: 文件路径
        content: 文件内容
        backup: 是否备份原文件
        
    Returns:
        成功返回True，失败返回False
    """
    return safe_file_manager.write_text_file(file_path, content, backup)


def append_file(file_path: Union[str, Path], content: str) -> bool:
    """
    便捷函数：追加到文件
    
    Args:
        file_path: 文件路径
        content: 要追加的内容
        
    Returns:
        成功返回True，失败返回False
    """
    return safe_file_manager.append_to_file(file_path, content)


def read_binary(file_path: Union[str, Path]) -> Optional[bytes]:
    """
    便捷函数：读取二进制文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容（bytes），失败返回None
    """
    return safe_file_manager.read_binary_file(file_path)


def write_binary(file_path: Union[str, Path], content: bytes) -> bool:
    """
    便捷函数：写入二进制文件
    
    Args:
        file_path: 文件路径
        content: 文件内容（bytes）
        
    Returns:
        成功返回True，失败返回False
    """
    return safe_file_manager.write_binary_file(file_path, content)


# 设置基本日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')