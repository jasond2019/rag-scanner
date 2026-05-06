"""
探测行为审计器
记录所有探测请求，支持审计追溯
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class ScanAuditor:
    """扫描审计日志记录器"""
    
    def __init__(self, log_dir: str = "data/audit_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
    
    async def log_request(self, task_id: str, detector: str, 
                         request_url: str, request_method: str,
                         request_payload: Optional[str] = None,
                         response_status: int = 200,
                         response_body: Optional[str] = None) -> None:
        """
        记录探测请求
        
        Args:
            task_id: 任务 ID
            detector: 检测器名称
            request_url: 请求 URL
            request_method: 请求方法
            request_payload: 请求体
            response_status: 响应状态码
            response_body: 响应体
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "detector": detector,
            "request": {
                "url": request_url,
                "method": request_method,
                "payload": request_payload,
            },
            "response": {
                "status": response_status,
                "body": response_body[:1000] if response_body else None,  # 限制长度
            }
        }
        
        async with self._lock:
            log_file = self.log_dir / f"{task_id}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    async def log_error(self, *args, **kwargs) -> None:
        """
        记录错误（兼容 positional 和 keyword 参数）
        
        支持两种调用方式：
        1. 位置参数: log_error(task_id, component, error_message) - 旧版检测器使用
        2. 关键字参数: log_error(task_id="...", detector="...", error="...") - 新版调用
        """
        task_id = None
        component = None
        error_msg = None
        
        # 检查是否是位置参数调用（旧版检测器使用）
        if args:
            if len(args) == 3:
                # 旧版调用：log_error(task_id, component, error_message)
                task_id, component, error_msg = args
            elif len(args) == 2:
                # 可能是 task_id, component，错误信息在 kwargs 中
                task_id, component = args
                error_msg = kwargs.get('error', kwargs.get('error_message', 'Unknown error'))
            else:
                # 只有一个参数
                task_id = args[0] if args else kwargs.get('task_id', 'unknown')
                component = kwargs.get('component', kwargs.get('detector', 'unknown'))
                error_msg = kwargs.get('error', kwargs.get('error_message', 'Unknown error'))
        else:
            # 关键字参数调用（新版）
            task_id = kwargs.get('task_id', 'unknown')
            component = kwargs.get('component', kwargs.get('detector', 'unknown'))
            error_msg = kwargs.get('error', kwargs.get('error_message', 'Unknown error'))
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "type": "error",
            "component": component,
            "error": error_msg,
        }
        
        async with self._lock:
            log_file = self.log_dir / f"{task_id}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def get_audit_log(self, task_id: str) -> list:
        """
        获取审计日志
        
        Args:
            task_id: 任务 ID
        
        Returns:
            list: 日志条目列表
        """
        log_file = self.log_dir / f"{task_id}.jsonl"
        if not log_file.exists():
            return []
        
        logs = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():  # 跳过空行
                    logs.append(json.loads(line))
        
        return logs