"""
扫描服务
处理扫描任务的提交、执行、结果获取
"""

import asyncio
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Optional

from flask import current_app, Flask
from flask_socketio import SocketIO

from .persistence import PersistenceService
from ..extensions import socketio
from ..models import ScanAuditLog

from scanner.engine import ScanEngine, ScanResult
from scanner.scorer import VulnerabilityScorer
from scanner.format_detector import APIFormatDetector  # 新增


class ScanService:
    """扫描任务服务"""

    def __init__(self):
        self.engine = ScanEngine()
        self.scorer = VulnerabilityScorer()
        self.persistence = PersistenceService()
        self.socketio = socketio

        # 审计日志目录
        self.audit_log_dir = Path(__file__).resolve().parent.parent.parent / "data" / "audit_logs"
        self.audit_log_dir.mkdir(parents=True, exist_ok=True)

    def submit_scan(self, target_type: str, target_value: str, step: int = 1,
                    anonymous_user_id: str = None, curl_data: Optional[Dict] = None,
                    param_name: str = None) -> dict:
        """
        提交扫描任务

        Args:
            target_type: 目标类型 (url, endpoint, config)
            target_value: 目标 URL 或配置内容
            step: 扫描步骤 (1=初步扫描, 2=配置补充)
            anonymous_user_id: 匿名用户 ID（用于恢复任务）
            curl_data: curl 解析后的请求格式（如果用户提供 curl 命令）

        Returns:
            dict: API 响应格式
        """
        # 生成任务 ID
        task_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 确定实际 URL
        actual_url = target_value
        if curl_data:
            actual_url = curl_data.get("url", target_value)
            # 如果用户指定了参数名，覆盖 curl 解析结果
            if param_name:
                curl_data["param_name"] = param_name

        # 创建任务数据
        task_data = {
            "task_id": task_id,
            "user_id": anonymous_user_id,  # 存储匿名用户 ID
            "target_type": target_type,
            "target_value": actual_url,
            "step": step,
            "status": "queued",
            "progress": 0,
            "current_step": "waiting",
            "created_at": datetime.utcnow().isoformat(),
        }

        # 保存到数据库
        self.persistence.save_task(task_data)

        # 获取当前 Flask 应用实例（用于后台线程）
        app = current_app._get_current_object()

        # 后台线程执行扫描
        def run_scan_thread():
            with app.app_context():
                asyncio.run(self._run_scan(task_id, target_type, actual_url, step, curl_data))

        thread = threading.Thread(target=run_scan_thread, daemon=True)
        thread.start()

        return {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": task_id,
                "status": "queued",
                "estimated_time": 180 if step == 1 else 120,
                "step": step
            }
        }

    def get_progress(self, task_id: str) -> dict:
        """
        获取扫描进度

        Args:
            task_id: 任务 ID

        Returns:
            dict: API 响应格式
        """
        task = self.persistence.get_task(task_id)

        if not task:
            return {"code": 1, "message": "任务不存在"}

        return {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": task_id,
                "status": task["status"],
                "progress": task["progress"],
                "current_step": task["current_step"],
                "step": task["step"],
                "score": task["score"]
            }
        }

    def get_result(self, task_id: str) -> dict:
        """
        获取扫描结果

        Args:
            task_id: 任务 ID

        Returns:
            dict: API 响应格式
        """
        task = self.persistence.get_task(task_id)

        if not task:
            return {"code": 1, "message": "任务不存在"}

        if task["status"] != "completed":
            return {"code": 1, "message": f"任务未完成，当前状态：{task['status']}"}

        result = task["result"]

        return {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": task_id,
                "step": result["step"],
                "is_final": result["step"] == 3,
                "score": result["score"],
                "level": result["level"],
                "vulnerabilities": result["vulnerabilities"],
                "score_breakdown": result["score_breakdown"],
                "report_url": f"/api/v1/report/generate?task_id={task_id}",
                "next_step_hint": "上传配置文件可获取更完整检测" if result["step"] == 1 else None
            }
        }

    def merge_results(self, task_id_step1: str, task_id_step2: str) -> dict:
        """
        合并两次扫描结果

        Args:
            task_id_step1: 第一次扫描的任务 ID
            task_id_step2: 第二次扫描的任务 ID

        Returns:
            dict: API 响应格式
        """
        task1 = self.persistence.get_task(task_id_step1)
        task2 = self.persistence.get_task(task_id_step2)

        if not task1 or not task2:
            return {"code": 1, "message": "任务不存在"}

        if task1["status"] != "completed" or task2["status"] != "completed":
            return {"code": 1, "message": "任务未完成"}

        result1 = task1["result"]
        result2 = task2["result"]

        # 合并漏洞列表
        all_vulns = result1["vulnerabilities"] + result2["vulnerabilities"]
        score_breakdown = self.scorer.calculate_breakdown(all_vulns)

        merged_task_id = f"{task_id_step1}_merged"

        # 创建合并任务
        merged_task_data = {
            "task_id": merged_task_id,
            "target_type": task1["target_type"],
            "target_value": task1["target_value"],
            "step": 3,
            "status": "completed",
            "score": score_breakdown["final_score"],
            "level": self.scorer.get_risk_level(score_breakdown["final_score"]),
            "created_at": task1["created_at"],
            "completed_at": datetime.utcnow().isoformat(),
        }

        self.persistence.save_task(merged_task_data)

        return {
            "code": 0,
            "message": "success",
            "data": {
                "merged_task_id": merged_task_id,
                "is_final": True,
                "score": score_breakdown["final_score"],
                "score_breakdown": score_breakdown,
                "vulnerabilities": all_vulns,
                "report_url": f"/api/v1/report/generate?task_id={merged_task_id}"
            }
        }

    def get_task_logs(self, task_id: str) -> dict:
        """
        获取任务审计日志

        Args:
            task_id: 任务 ID

        Returns:
            dict: API 响应格式
        """
        logs_out = []
        log_file_display = None

        try:
            # 从数据库获取日志路径
            rows = ScanAuditLog.query.filter_by(task_id=task_id).order_by(ScanAuditLog.timestamp.asc()).all()

            # 查找 jsonl 文件
            for r in rows:
                url = (r.request_url or "").strip()
                if url.lower().endswith(".jsonl"):
                    log_path = Path(url)
                    if log_path.exists():
                        logs_out = self._read_jsonl_file(log_path)
                        log_file_display = str(log_path.resolve())
                        break

            # 如果没有找到，使用默认路径
            if not logs_out:
                canonical = self.audit_log_dir / f"{task_id}.jsonl"
                if canonical.exists():
                    logs_out = self._read_jsonl_file(canonical)
                    log_file_display = str(canonical.resolve())

            # 如果还是没有，从引擎获取
            if not logs_out:
                raw = self.engine.auditor.get_audit_log(task_id)
                logs_out = [x for x in raw if isinstance(x, dict)]

            # 规范化日志格式
            if logs_out:
                logs_out = [self._normalize_log_entry(x) for x in logs_out]
            elif rows:
                logs_out = [r.to_dict() for r in rows]

        except Exception as e:
            print(f"[ScanService] Error getting logs: {e}")

        return {
            "code": 0,
            "message": "success",
            "data": {
                "logs": logs_out,
                "log_file": log_file_display
            }
        }

    async def _run_scan(self, task_id: str, target_type: str, target_value: str,
                         step: int, curl_data: Optional[Dict] = None):
        """
        执行扫描任务（异步）

        Args:
            task_id: 任务 ID
            target_type: 目标类型
            target_value: 目标 URL
            step: 扫描步骤
            curl_data: curl 解析后的请求格式
        """
        # 进度回调函数
        async def progress_callback(progress: int, current_step: str):
            self.persistence.update_task(task_id, {
                "progress": progress,
                "current_step": current_step
            })

            self.socketio.emit("progress", {
                "task_id": task_id,
                "progress": progress,
                "current_step": current_step
            })

        try:
            # 更新状态为运行中
            self.persistence.update_task(task_id, {"status": "running"})
            self.socketio.emit("status", {"task_id": task_id, "status": "running"})

            # 执行扫描（传递 curl_data）
            result = await self.engine.scan(
                task_id=task_id,
                target_type=target_type,
                target_value=target_value,
                curl_data=curl_data,  # 新增
                step=step,
                progress_callback=progress_callback
            )

            # 更新状态为完成
            self.persistence.update_task(task_id, {
                "status": "completed",
                "score": result.score,
                "level": result.level,
                "result": result,
                "completed_at": datetime.utcnow().isoformat(),
            })

            self.socketio.emit("status", {"task_id": task_id, "status": "completed"})

        except Exception as e:
            # 更新状态为失败
            self.persistence.update_task(task_id, {"status": "failed"})
            self.socketio.emit("status", {"task_id": task_id, "status": "failed", "error": str(e)})

    def _read_jsonl_file(self, path: Path) -> List[dict]:
        """读取 jsonl 文件"""
        if not path.is_file():
            return []

        logs = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return logs

    def _normalize_log_entry(self, entry: dict) -> dict:
        """规范化日志条目格式"""
        out = dict(entry)
        req = entry.get("request")
        if isinstance(req, dict):
            out.setdefault("request_url", req.get("url"))
            out.setdefault("request_method", req.get("method"))
        resp = entry.get("response")
        if isinstance(resp, dict) and "status" in resp:
            out.setdefault("response_status", resp["status"])
        if entry.get("type") == "error":
            out.setdefault("level", "error")
            out.setdefault("message", entry.get("error", ""))
        return out