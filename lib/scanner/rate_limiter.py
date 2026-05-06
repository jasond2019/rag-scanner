"""
速率限制器
原则：单目标 ≤ 10 请求/秒，避免 DoS 风险
"""

import asyncio
import time
from typing import Dict
from collections import defaultdict


class RateLimiter:
    """令牌桶速率限制器"""
    
    def __init__(self, max_requests_per_second: int = 10):
        self.max_rps = max_requests_per_second
        self.buckets: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def acquire(self, target: str) -> bool:
        """
        获取令牌（等待可用令牌）
        
        Args:
            target: 目标标识（URL 或域名）
        
        Returns:
            bool: 是否获取成功
        """
        async with self._lock:
            now = time.time()
            bucket = self.buckets[target]
            
            # 清理 1 秒前的请求记录
            bucket[:] = [t for t in bucket if now - t < 1.0]
            
            if len(bucket) < self.max_rps:
                bucket.append(now)
                return True
            
            # 需要等待
            oldest = bucket[0]
            wait_time = 1.0 - (now - oldest)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                bucket.pop(0)
                bucket.append(time.time())
            
            return True
    
    def get_remaining(self, target: str) -> int:
        """
        获取剩余可用请求数
        
        Args:
            target: 目标标识
        
        Returns:
            int: 剩余请求数
        """
        now = time.time()
        bucket = self.buckets[target]
        bucket[:] = [t for t in bucket if now - t < 1.0]
        return max(0, self.max_rps - len(bucket))
