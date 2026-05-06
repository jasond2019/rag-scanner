"""
数据持久化服务
统一管理数据库操作，移除内存 tasks dict
Version: 2.0 - 修复 evidence JSON 解析问题
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from ..extensions import db
from ..models import ScanTask, Vulnerability, ScoreBreakdown, ScanAuditLog


class PersistenceService:
    """统一持久化服务"""

    def __init__(self):
        self.db = db

    def save_task(self, task_data: dict) -> bool:
        """
        创建新任务

        Args:
            task_data: 任务数据字典

        Returns:
            bool: 是否成功
        """
        try:
            task = ScanTask(
                id=task_data.get("task_id"),
                user_id=task_data.get("user_id"),  # 支持匿名用户 ID
                target_type=task_data.get("target_type"),
                target_value=task_data.get("target_value"),
                step=task_data.get("step", 1),
                status=task_data.get("status", "queued"),
                progress=task_data.get("progress", 0),
                current_step=task_data.get("current_step", "waiting"),
                created_at=datetime.fromisoformat(task_data["created_at"])
                    if task_data.get("created_at") else datetime.utcnow()
            )
            self.db.session.add(task)
            self.db.session.commit()
            return True
        except Exception as e:
            print(f"[Persistence] Error saving task: {e}")
            self.db.session.rollback()
            return False

    def update_task(self, task_id: str, updates: dict) -> bool:
        """
        更新任务状态

        Args:
            task_id: 任务 ID
            updates: 更新字段字典

        Returns:
            bool: 是否成功
        """
        try:
            task = ScanTask.query.get(task_id)
            if not task:
                return False

            for key, value in updates.items():
                if key == "created_at" and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                elif key == "completed_at" and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                elif key == "result":
                    # result 是特殊字段，需要解析并保存关联数据
                    self._save_result(task_id, value)
                    continue

                if hasattr(task, key):
                    setattr(task, key, value)

            self.db.session.commit()
            return True
        except Exception as e:
            print(f"[Persistence] Error updating task: {e}")
            self.db.session.rollback()
            return False

    def get_task(self, task_id: str) -> Optional[dict]:
        """
        获取单个任务

        Args:
            task_id: 任务 ID

        Returns:
            dict: 任务数据字典
        """
        task = ScanTask.query.get(task_id)
        if not task:
            return None

        return self._task_to_dict(task)

    def get_recent_tasks(self, limit: int = 20) -> List[dict]:
        """
        获取最近的任务列表

        Args:
            limit: 最大返回数量

        Returns:
            List[dict]: 任务列表
        """
        tasks = ScanTask.query.order_by(ScanTask.created_at.desc()).limit(limit).all()
        return [self._task_to_dict(t) for t in tasks]

    def get_user_in_progress_tasks(self, user_id: str) -> List[dict]:
        """
        获取用户进行中和排队的任务

        Args:
            user_id: 用户 ID（可以是匿名用户 ID）

        Returns:
            List[dict]: 进行中的任务列表
        """
        tasks = ScanTask.query.filter(
            ScanTask.user_id == user_id,
            ScanTask.status.in_(["queued", "running"])
        ).order_by(ScanTask.created_at.desc()).all()
        return [self._task_to_dict(t) for t in tasks]

    def get_all_in_progress_tasks(self) -> List[dict]:
        """
        获取所有进行中和排队的任务

        Returns:
            List[dict]: 所有进行中的任务列表
        """
        tasks = ScanTask.query.filter(
            ScanTask.status.in_(["queued", "running"])
        ).order_by(ScanTask.created_at.desc()).all()
        return [self._task_to_dict(t) for t in tasks]

    def get_user_tasks(self, user_id: str, limit: int = 10) -> List[dict]:
        """
        获取用户的所有任务（历史记录）

        Args:
            user_id: 用户 ID
            limit: 最大返回数量

        Returns:
            List[dict]: 用户任务列表
        """
        tasks = ScanTask.query.filter(
            ScanTask.user_id == user_id
        ).order_by(ScanTask.created_at.desc()).limit(limit).all()
        return [self._task_to_dict(t) for t in tasks]

    def _task_to_dict(self, task: ScanTask) -> dict:
        """
        将 ORM 任务对象转换为字典

        Args:
            task: ScanTask ORM 对象

        Returns:
            dict: 任务数据字典
        """
        import ast
        result_obj = None
        if task.status == "completed":
            vulnerabilities = []
            for vuln in task.vulnerabilities:
                # 直接处理 evidence 解析，兼容 JSON 和 Python repr 格式
                evidence_data = []
                if vuln.evidence:
                    try:
                        evidence_data = json.loads(vuln.evidence)
                    except json.JSONDecodeError:
                        try:
                            evidence_data = ast.literal_eval(vuln.evidence)
                        except (ValueError, SyntaxError):
                            evidence_data = [vuln.evidence]

                vuln_dict = {
                    'id': vuln.id,
                    'rule_id': vuln.rule_id,
                    'type': vuln.type,
                    'name': vuln.name,
                    'severity': vuln.severity,
                    'score_deduction': vuln.score_deduction,
                    'description': vuln.description,
                    'suggestion': vuln.suggestion,
                    'evidence': evidence_data,
                }
                vulnerabilities.append(vuln_dict)

            score_breakdown = None
            if task.score_breakdown:
                score_breakdown = task.score_breakdown.to_dict()

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
            "user_id": task.user_id,  # 添加用户 ID
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
        """
        保存扫描结果（漏洞和评分明细）

        Args:
            task_id: 任务 ID
            result: ScanResult 对象或字典
        """
        if result is None:
            return

        # 获取漏洞列表
        vulnerabilities = []
        if hasattr(result, "vulnerabilities"):
            vulnerabilities = result.vulnerabilities
        elif isinstance(result, dict):
            vulnerabilities = result.get("vulnerabilities", [])

        # 保存漏洞
        for vuln in vulnerabilities:
            vuln_id = f"{task_id}_{vuln.get('rule_id', 'unknown')}"
            existing_vuln = Vulnerability.query.get(vuln_id)
            if not existing_vuln:
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
                self.db.session.add(vuln_record)

        # 获取评分明细
        score_breakdown = None
        if hasattr(result, "score_breakdown"):
            score_breakdown = result.score_breakdown
        elif isinstance(result, dict):
            score_breakdown = result.get("score_breakdown")

        # 保存评分明细
        if score_breakdown:
            existing_sb = ScoreBreakdown.query.get(task_id)
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
                self.db.session.add(sb_record)

    def get_task_detail(self, task_id: str) -> Optional[dict]:
        """
        获取任务详情（含检测器分组和审计日志）

        Args:
            task_id: 任务 ID

        Returns:
            dict: 任务详情数据
        """
        import ast
        from collections import defaultdict

        task = ScanTask.query.get(task_id)
        if not task:
            return None

        # 检测器名称映射
        detector_names = {
            "RAG-SEC-001": "提示词注入检测",
            "RAG-SEC-002": "数据泄露检测",
            "RAG-SEC-003": "向量注入检测",
            "RAG-SEC-004": "检索污染检测",
            "RAG-SEC-005": "权限绕过检测",
            "RAG-SEC-006": "API滥用检测",
            "RAG-SEC-007": "日志泄露检测",
            "RAG-SEC-008": "模型越狱检测",
            "RAG-SEC-009": "依赖漏洞检测",
            "RAG-SEC-010": "配置错误检测",
        }

        # 获取漏洞列表
        vulnerabilities = {}
        for vuln in task.vulnerabilities:
            # 解析 evidence
            evidence_data = []
            if vuln.evidence:
                try:
                    evidence_data = json.loads(vuln.evidence)
                except json.JSONDecodeError:
                    try:
                        evidence_data = ast.literal_eval(vuln.evidence)
                    except (ValueError, SyntaxError):
                        evidence_data = [vuln.evidence]

            vulnerabilities[vuln.rule_id] = {
                'rule_id': vuln.rule_id,
                'name': vuln.name,
                'severity': vuln.severity,
                'score_deduction': vuln.score_deduction,
                'description': vuln.description,
                'suggestion': vuln.suggestion,
                'evidence': evidence_data,
            }

        # 从审计日志文件读取数据
        audit_logs_by_detector = defaultdict(list)
        audit_log_file = Path("data/audit_logs") / f"{task_id}.jsonl"
        if audit_log_file.exists():
            try:
                with open(audit_log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            log_entry = json.loads(line)
                            if log_entry.get("type") == "error":
                                continue  # 跳过错误日志
                            detector = log_entry.get("detector", "unknown")
                            audit_logs_by_detector[detector].append({
                                'request_url': log_entry.get("request", {}).get("url"),
                                'request_method': log_entry.get("request", {}).get("method"),
                                'request_payload': log_entry.get("request", {}).get("payload"),
                                'response_status': log_entry.get("response", {}).get("status"),
                                'response_body': log_entry.get("response", {}).get("body"),
                                'timestamp': log_entry.get("timestamp"),
                            })
            except Exception as e:
                print(f"[Persistence] Error reading audit log file: {e}")

        # 兼容：也检查数据库中的审计日志（如果有的话）
        for log in task.audit_logs:
            detector = log.detector or "unknown"
            audit_logs_by_detector[detector].append({
                'id': log.id,
                'request_url': log.request_url,
                'request_method': log.request_method,
                'request_payload': log.request_payload,
                'response_status': log.response_status,
                'response_body': log.response_body[:500] if log.response_body else None,
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
            })

        # 构建检测器结果列表（包含所有10个检测器）
        all_detector_ids = ["RAG-SEC-001", "RAG-SEC-002", "RAG-SEC-003", "RAG-SEC-004",
                          "RAG-SEC-005", "RAG-SEC-006", "RAG-SEC-007", "RAG-SEC-008",
                          "RAG-SEC-009", "RAG-SEC-010"]

        detectors = []
        for detector_id in all_detector_ids:
            vuln = vulnerabilities.get(detector_id)
            logs = audit_logs_by_detector.get(detector_id, [])

            detector_info = {
                'detector_id': detector_id,
                'detector_name': detector_names.get(detector_id, detector_id),
                'status': 'vulnerable' if vuln else ('tested' if logs else 'skipped'),
                'severity': vuln.get('severity') if vuln else None,
                'score_deduction': vuln.get('score_deduction', 0) if vuln else 0,
                'description': vuln.get('description') if vuln else None,
                'suggestion': vuln.get('suggestion') if vuln else None,
                'evidence': vuln.get('evidence') if vuln else None,
                'tests': logs,  # 该检测器的所有探测记录
            }
            detectors.append(detector_info)

        # 构建评分明细
        score_breakdown = None
        if task.score_breakdown:
            score_breakdown = task.score_breakdown.to_dict()

        return {
            'task': {
                'id': task.id,
                'target_type': task.target_type,
                'target_value': task.target_value,
                'status': task.status,
                'score': task.score,
                'level': task.level,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            },
            'score_breakdown': score_breakdown,
            'detectors': detectors,
            'vulnerability_count': len(vulnerabilities),
        }