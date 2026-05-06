"""
持久化服务
适配 Vercel Postgres
"""

from datetime import datetime
from typing import Dict, Optional, Any
import json

from sqlalchemy.orm import Session
from lib.db import SessionLocal
from lib.models import ScanTask, Vulnerability, ScoreBreakdown, ScanAuditLog


class PersistenceService:
    """统一持久化服务"""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()

    def save_task(self, task_data: dict) -> bool:
        """创建新任务"""
        try:
            task = ScanTask(
                id=task_data.get("task_id"),
                user_id=task_data.get("user_id"),
                target_type=task_data.get("target_type"),
                target_value=task_data.get("target_value"),
                step=task_data.get("step", 1),
                status=task_data.get("status", "queued"),
                progress=task_data.get("progress", 0),
                current_step=task_data.get("current_step", "waiting"),
                created_at=datetime.fromisoformat(task_data["created_at"])
                    if task_data.get("created_at") else datetime.utcnow()
            )
            self.db.add(task)
            self.db.commit()
            return True
        except Exception as e:
            print(f"[Persistence] Error saving task: {e}")
            self.db.rollback()
            return False

    def update_task(self, task_id: str, updates: dict) -> bool:
        """更新任务状态"""
        try:
            task = self.db.query(ScanTask).filter(ScanTask.id == task_id).first()
            if not task:
                return False

            for key, value in updates.items():
                if key == "created_at" and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                elif key == "completed_at" and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                elif key == "result":
                    self._save_result(task_id, value)
                    continue

                if hasattr(task, key):
                    setattr(task, key, value)

            self.db.commit()
            return True
        except Exception as e:
            print(f"[Persistence] Error updating task: {e}")
            self.db.rollback()
            return False

    def get_task(self, task_id: str) -> Optional[dict]:
        """获取单个任务"""
        task = self.db.query(ScanTask).filter(ScanTask.id == task_id).first()
        if not task:
            return None
        return self._task_to_dict(task)

    def _task_to_dict(self, task: ScanTask) -> dict:
        """将 ORM 任务对象转换为字典"""
        import ast
        result_obj = None
        if task.status == "completed":
            vulnerabilities = [v.to_dict() for v in task.vulnerabilities]
            score_breakdown = task.score_breakdown.to_dict() if task.score_breakdown else None

            result_obj = {
                "step": task.step,
                "score": task.score,
                "level": task.level,
                "vulnerabilities": vulnerabilities,
                "score_breakdown": score_breakdown
            }

        return {
            "id": task.id,
            "task_id": task.id,
            "user_id": task.user_id,
            "target_type": task.target_type,
            "target_value": task.target_value,
            "step": task.step,
            "status": task.status,
            "progress": task.progress,
            "current_step": task.current_step,
            "score": task.score,
            "level": task.level,
            "result": result_obj,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }

    def _save_result(self, task_id: str, result: Any) -> None:
        """保存扫描结果"""
        if result is None:
            return

        vulnerabilities = []
        if hasattr(result, "vulnerabilities"):
            vulnerabilities = result.vulnerabilities
        elif isinstance(result, dict):
            vulnerabilities = result.get("vulnerabilities", [])

        for vuln in vulnerabilities:
            vuln_id = f"{task_id}_{vuln.get('rule_id', 'unknown')}"
            existing = self.db.query(Vulnerability).filter(Vulnerability.id == vuln_id).first()
            if not existing:
                vuln_record = Vulnerability(
                    id=vuln_id,
                    task_id=task_id,
                    rule_id=vuln.get("rule_id", ""),
                    type=vuln.get("type", ""),
                    name=vuln.get("name", ""),
                    severity=vuln.get("severity", ""),
                    score_deduction=vuln.get("score_deduction", 0),
                    description=vuln.get("description", ""),
                    suggestion=vuln.get("suggestion", ""),
                    evidence=json.dumps(vuln.get("evidence", []))
                )
                self.db.add(vuln_record)

        score_breakdown = None
        if hasattr(result, "score_breakdown"):
            score_breakdown = result.score_breakdown
        elif isinstance(result, dict):
            score_breakdown = result.get("score_breakdown")

        if score_breakdown:
            existing_sb = self.db.query(ScoreBreakdown).filter(ScoreBreakdown.task_id == task_id).first()
            if not existing_sb:
                sb_record = ScoreBreakdown(
                    id=task_id,
                    task_id=task_id,
                    base_score=score_breakdown.get("base_score", 100),
                    critical_count=score_breakdown.get("critical_count", 0),
                    critical_deduction=score_breakdown.get("critical_deduction", 0),
                    high_count=score_breakdown.get("high_count", 0),
                    high_deduction=score_breakdown.get("high_deduction", 0),
                    medium_count=score_breakdown.get("medium_count", 0),
                    medium_deduction=score_breakdown.get("medium_deduction", 0),
                    low_count=score_breakdown.get("low_count", 0),
                    low_deduction=score_breakdown.get("low_deduction", 0),
                    total_deduction=score_breakdown.get("total_deduction", 0),
                    final_score=score_breakdown.get("final_score", 100)
                )
                self.db.add(sb_record)

    def save_audit_log(self, task_id: str, log: dict) -> bool:
        """保存审计日志"""
        try:
            import uuid
            log_record = ScanAuditLog(
                id=f"{task_id}_{uuid.uuid4().hex[:8]}",
                task_id=task_id,
                detector=log.get('detector'),
                request_url=log.get('request', {}).get('url'),
                request_method=log.get('request', {}).get('method'),
                request_payload=json.dumps(log.get('request', {}).get('payload')),
                response_status=log.get('response', {}).get('status'),
                response_body=log.get('response', {}).get('body'),
            )
            self.db.add(log_record)
            self.db.commit()
            return True
        except Exception as e:
            print(f"[Persistence] Error saving audit log: {e}")
            self.db.rollback()
            return False

    def get_audit_logs(self, task_id: str) -> list:
        """获取审计日志"""
        logs = self.db.query(ScanAuditLog).filter(ScanAuditLog.task_id == task_id).all()
        return [log.to_dict() for log in logs]