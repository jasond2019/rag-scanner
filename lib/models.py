"""
数据模型
适配 Vercel Postgres (SQLAlchemy)
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from lib.db import Base


class ScanTask(Base):
    """扫描任务表"""
    __tablename__ = 'scan_tasks'

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=True)
    target_type = Column(String(32), nullable=False)
    target_value = Column(Text, nullable=False)
    step = Column(Integer, default=1)
    status = Column(String(32), default='queued')
    progress = Column(Integer, default=0)
    current_step = Column(String(64), default='waiting')
    score = Column(Integer, nullable=True)
    level = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # 关联
    vulnerabilities = relationship('Vulnerability', backref='task', cascade='all, delete-orphan')
    score_breakdown = relationship('ScoreBreakdown', backref='task', uselist=False, cascade='all, delete-orphan')
    audit_logs = relationship('ScanAuditLog', backref='task', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'target_type': self.target_type,
            'target_value': self.target_value,
            'step': self.step,
            'status': self.status,
            'progress': self.progress,
            'current_step': self.current_step,
            'score': self.score,
            'level': self.level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class Vulnerability(Base):
    """漏洞结果表"""
    __tablename__ = 'vulnerabilities'

    id = Column(String(64), primary_key=True)
    task_id = Column(String(64), ForeignKey('scan_tasks.id'), nullable=False)
    rule_id = Column(String(32), nullable=False)
    type = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    severity = Column(String(32), nullable=False)
    score_deduction = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        import ast
        evidence_data = []
        if self.evidence:
            try:
                evidence_data = json.loads(self.evidence)
            except json.JSONDecodeError:
                try:
                    evidence_data = ast.literal_eval(self.evidence)
                except (ValueError, SyntaxError):
                    evidence_data = [self.evidence]
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'type': self.type,
            'name': self.name,
            'severity': self.severity,
            'score_deduction': self.score_deduction,
            'description': self.description,
            'suggestion': self.suggestion,
            'evidence': evidence_data,
        }


class ScoreBreakdown(Base):
    """评分明细表"""
    __tablename__ = 'score_breakdowns'

    id = Column(String(64), primary_key=True)
    task_id = Column(String(64), ForeignKey('scan_tasks.id'), unique=True, nullable=False)
    base_score = Column(Integer, default=100)
    critical_count = Column(Integer, default=0)
    critical_deduction = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    high_deduction = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    medium_deduction = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    low_deduction = Column(Integer, default=0)
    total_deduction = Column(Integer, default=0)
    final_score = Column(Integer, default=100)

    def to_dict(self):
        return {
            'base_score': self.base_score,
            'critical_count': self.critical_count,
            'critical_deduction': self.critical_deduction,
            'high_count': self.high_count,
            'high_deduction': self.high_deduction,
            'medium_count': self.medium_count,
            'medium_deduction': self.medium_deduction,
            'low_count': self.low_count,
            'low_deduction': self.low_deduction,
            'total_deduction': self.total_deduction,
            'final_score': self.final_score,
        }


class ScanAuditLog(Base):
    """探测审计日志表"""
    __tablename__ = 'scan_audit_logs'

    id = Column(String(64), primary_key=True)
    task_id = Column(String(64), ForeignKey('scan_tasks.id'), nullable=False)
    detector = Column(String(64), nullable=True)
    request_url = Column(Text, nullable=True)
    request_method = Column(String(16), nullable=True)
    request_payload = Column(Text, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'detector': self.detector,
            'request_url': self.request_url,
            'request_method': self.request_method,
            'request_payload': self.request_payload,
            'response_status': self.response_status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }