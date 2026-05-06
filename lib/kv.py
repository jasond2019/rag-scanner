"""
Vercel KV (Redis) 连接
用于任务进度缓存和状态管理
"""

import os
import json
import time
from typing import Optional, Dict, Any

# Vercel KV 使用 REST API
KV_REST_API_URL = os.environ.get('KV_REST_API_URL')
KV_REST_API_TOKEN = os.environ.get('KV_REST_API_TOKEN')


class KVClient:
    """Vercel KV 客户端"""

    def __init__(self):
        self.url = KV_REST_API_URL
        self.token = KV_REST_API_TOKEN

    async def _request(self, method: str, key: str, value: Any = None, ex: int = None) -> Any:
        """发送 KV REST API 请求"""
        import aiohttp

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        url = f'{self.url}/{key}'

        async with aiohttp.ClientSession() as session:
            if method == 'GET':
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return json.loads(data.get('result', 'null'))
                    return None
            elif method == 'SET':
                body = {'value': json.dumps(value)}
                if ex:
                    body['ex'] = ex
                async with session.post(url, headers=headers, json=body) as resp:
                    return resp.status == 200
            elif method == 'DEL':
                async with session.delete(url, headers=headers) as resp:
                    return resp.status == 200

        return None

    async def set(self, key: str, value: Dict, ex: int = 3600) -> bool:
        """设置键值，ex 为过期时间（秒）"""
        return await self._request('SET', key, value, ex)

    async def get(self, key: str) -> Optional[Dict]:
        """获取键值"""
        return await self._request('GET', key)

    async def delete(self, key: str) -> bool:
        """删除键"""
        return await self._request('DEL', key)


# 全局 KV 客户端
kv = KVClient()


# 进度管理函数
async def set_progress(task_id: str, progress: int, current_step: str, status: str = 'running') -> bool:
    """设置任务进度"""
    return await kv.set(f'progress:{task_id}', {
        'progress': progress,
        'current_step': current_step,
        'status': status,
        'timestamp': time.time()
    }, ex=3600)


async def get_progress(task_id: str) -> Optional[Dict]:
    """获取任务进度"""
    return await kv.get(f'progress:{task_id}')


async def set_task_status(task_id: str, status: str, error: str = None) -> bool:
    """设置任务状态"""
    data = {'status': status, 'timestamp': time.time()}
    if error:
        data['error'] = error
    return await kv.set(f'status:{task_id}', data, ex=3600)


async def get_task_status(task_id: str) -> Optional[Dict]:
    """获取任务状态"""
    return await kv.get(f'status:{task_id}')