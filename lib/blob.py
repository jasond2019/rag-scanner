"""
Vercel Blob 存储
用于 PDF 报告和审计日志存储
"""

import os
from typing import Optional

# Vercel Blob 使用 REST API
BLOB_READ_WRITE_TOKEN = os.environ.get('BLOB_READ_WRITE_TOKEN')


class BlobClient:
    """Vercel Blob 客户端"""

    def __init__(self):
        self.token = BLOB_READ_WRITE_TOKEN

    async def upload(self, pathname: str, content: bytes) -> Optional[str]:
        """上传文件到 Blob"""
        import aiohttp

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/pdf'
        }

        url = 'https://blob.vercel-storage.com'

        async with aiohttp.ClientSession() as session:
            async with session.put(
                f'{url}/{pathname}',
                headers=headers,
                data=content
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('url')
                return None

    async def get_url(self, pathname: str) -> Optional[str]:
        """获取文件 URL"""
        # Vercel Blob URL 格式
        return f'https://blob.vercel-storage.com/{pathname}'


# 全局 Blob 客户端
blob = BlobClient()


async def upload_report(task_id: str, pdf_bytes: bytes) -> Optional[str]:
    """上传 PDF 报告"""
    return await blob.upload(f'reports/{task_id}.pdf', pdf_bytes)


async def get_report_url(task_id: str) -> str:
    """获取报告 URL"""
    return await blob.get_url(f'reports/{task_id}.pdf')