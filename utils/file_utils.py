"""
文件操作工具模块
统一处理文件编码问题，确保所有文件操作都使用UTF-8编码
"""

import os
import codecs
from typing import Optional


def read_file_utf8(file_path: str) -> str:
    """
    安全读取文件，确保使用UTF-8编码
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容字符串
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file_utf8(file_path: str, content: str) -> bool:
    """
    安全写入文件，使用UTF-8编码
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
        
    Returns:
        成功返回True，失败返回False
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False


def safe_read_file(file_path: str) -> Optional[str]:
    """
    安全读取文件，自动检测编码格式
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容字符串，失败返回None
    """
    encodings = ['utf-8', 'gbk', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                return content
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"读取文件失败 ({encoding}): {e}")
            continue
    
    print(f"无法读取文件: {file_path}")
    return None


def check_file_encoding(file_path: str) -> dict:
    """
    检查文件编码信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        包含编码信息的字典
    """
    import chardet
    
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        
    return {
        'encoding': result['encoding'],
        'confidence': result['confidence'],
        'language': result.get('language', 'Unknown')
    }


def convert_to_utf8(file_path: str) -> bool:
    """
    将文件转换为UTF-8编码
    
    Args:
        file_path: 文件路径
        
    Returns:
        成功返回True，失败返回False
    """
    try:
        # 首先尝试检测当前编码
        import chardet
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
        
        # 使用检测到的编码读取文件
        original_encoding = detected['encoding'] or 'utf-8'
        if original_encoding.lower() == 'utf-8':
            return True  # 已经是UTF-8
        
        # 读取原内容并转为UTF-8
        with open(file_path, 'r', encoding=original_encoding) as f:
            content = f.read()
        
        # 以UTF-8编码写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"文件已转换为UTF-8编码: {file_path}")
        return True
        
    except Exception as e:
        print(f"转换文件编码失败: {e}")
        return False


def ensure_directory_exists(file_path: str) -> bool:
    """
    确保文件所在目录存在
    
    Args:
        file_path: 文件路径
        
    Returns:
        成功返回True，失败返回False
    """
    try:
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        print(f"创建目录失败: {e}")
        return False