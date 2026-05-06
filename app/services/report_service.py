"""
报告服务
处理 PDF 报告的生成和下载
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from .persistence import PersistenceService
from ..report_generator import ReportGenerator
from ..config import REPORTS_FOLDER


class ReportService:
    """报告服务"""

    def __init__(self):
        self.persistence = PersistenceService()
        self.report_generator = ReportGenerator(REPORTS_FOLDER)
        self.reports_folder = Path(REPORTS_FOLDER)
        self.reports_folder.mkdir(exist_ok=True)

    def generate_report(self, task_id: str) -> dict:
        """
        生成 PDF 报告

        Args:
            task_id: 任务 ID

        Returns:
            dict: API 响应格式
        """
        task = self.persistence.get_task(task_id)

        if not task:
            return {"code": 1, "message": "任务不存在"}

        if task["status"] != "completed":
            return {"code": 1, "message": "任务未完成"}

        result = task["result"]
        result_dict = {
            "task_id": task_id,
            "score": result["score"],
            "level": result["level"],
            "vulnerabilities": result["vulnerabilities"],
            "score_breakdown": result["score_breakdown"],
        }

        try:
            pdf_path = self.report_generator.generate(result_dict, template="default", watermark=True)
            report_id = os.path.basename(pdf_path).replace(".pdf", "")
            expire_at = datetime.utcnow() + timedelta(days=7)

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "report_id": report_id,
                    "download_url": f"/api/v1/report/download/{report_id}",
                    "expire_at": expire_at.isoformat()
                }
            }
        except Exception as e:
            return {"code": 1, "message": f"PDF 生成失败：{str(e)}"}

    def get_report_path(self, report_id: str) -> str:
        """
        获取报告文件路径

        Args:
            report_id: 报告 ID（可能包含扩展名）

        Returns:
            str: 报告文件路径（如果存在）
        """
        # 如果 report_id 已包含扩展名，直接尝试该路径
        if '.' in report_id:
            report_path = self.reports_folder / report_id
            if report_path.exists():
                return str(report_path)

        # 尝试 PDF 格式
        pdf_path = self.reports_folder / f"{report_id}.pdf"
        if pdf_path.exists():
            return str(pdf_path)

        # 尝试 TXT 格式（WeasyPrint 不可用时的备选）
        txt_path = self.reports_folder / f"{report_id}.txt"
        if txt_path.exists():
            return str(txt_path)

        return None