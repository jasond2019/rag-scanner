"""
数据库模型
使用 extensions.py 中的 SQLAlchemy 实例
"""

from datetime import datetime

# 从 extensions 导入 db（必须在模型类定义之前）
from .extensions import db


class ScanTask(db.Model):
    """扫描任务表"""

    __tablename__ = 'scan_tasks'

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.String(64), db.ForeignKey('users.id'), nullable=True)
    target_type = db.Column(db.String(32), nullable=False)  # url, endpoint, config
    target_value = db.Column(db.Text, nullable=False)
    step = db.Column(db.Integer, default=1)  # 1, 2, 3(merged)
    previous_task_id = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), default='queued')  # queued, running, completed, failed
    progress = db.Column(db.Integer, default=0)
    current_step = db.Column(db.String(64), default='waiting')
    score = db.Column(db.Integer, nullable=True)
    level = db.Column(db.String(32), nullable=True)  # high, medium, low
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # 关联
    vulnerabilities = db.relationship('Vulnerability', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    score_breakdown = db.relationship('ScoreBreakdown', backref='task', uselist=False, cascade='all, delete-orphan')
    audit_logs = db.relationship('ScanAuditLog', backref='task', lazy='dynamic', cascade='all, delete-orphan')

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


class Vulnerability(db.Model):
    """漏洞结果表"""

    __tablename__ = 'vulnerabilities'

    id = db.Column(db.String(64), primary_key=True)
    task_id = db.Column(db.String(64), db.ForeignKey('scan_tasks.id'), nullable=False)
    rule_id = db.Column(db.String(32), nullable=False)
    type = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    severity = db.Column(db.String(32), nullable=False)  # critical, high, medium, low
    score_deduction = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, nullable=True)
    suggestion = db.Column(db.Text, nullable=True)
    evidence = db.Column(db.Text, nullable=True)  # JSON array
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        import ast
        # 解析 evidence，兼容 JSON 和 Python repr 两种格式
        evidence_data = []
        if self.evidence:
            try:
                # 尝试 JSON 解析（新数据）
                evidence_data = json.loads(self.evidence)
            except json.JSONDecodeError:
                # 兼容 Python repr 格式（历史数据）
                try:
                    evidence_data = ast.literal_eval(self.evidence)
                except (ValueError, SyntaxError):
                    # 解析失败时返回原始字符串
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


class ScoreBreakdown(db.Model):
    """评分明细表"""

    __tablename__ = 'score_breakdowns'

    id = db.Column(db.String(64), primary_key=True)
    task_id = db.Column(db.String(64), db.ForeignKey('scan_tasks.id'), unique=True, nullable=False)
    base_score = db.Column(db.Integer, default=100)
    critical_count = db.Column(db.Integer, default=0)
    critical_deduction = db.Column(db.Integer, default=0)
    high_count = db.Column(db.Integer, default=0)
    high_deduction = db.Column(db.Integer, default=0)
    medium_count = db.Column(db.Integer, default=0)
    medium_deduction = db.Column(db.Integer, default=0)
    low_count = db.Column(db.Integer, default=0)
    low_deduction = db.Column(db.Integer, default=0)
    total_deduction = db.Column(db.Integer, default=0)
    final_score = db.Column(db.Integer, default=100)

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


class ScanAuditLog(db.Model):
    """探测审计日志表"""

    __tablename__ = 'scan_audit_logs'

    id = db.Column(db.String(64), primary_key=True)
    task_id = db.Column(db.String(64), db.ForeignKey('scan_tasks.id'), nullable=False)
    detector = db.Column(db.String(64), nullable=True)
    request_url = db.Column(db.Text, nullable=True)
    request_method = db.Column(db.String(16), nullable=True)
    request_payload = db.Column(db.Text, nullable=True)
    response_status = db.Column(db.Integer, nullable=True)
    response_body = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

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


class User(db.Model):
    """用户表（P1 功能）"""

    __tablename__ = 'users'

    id = db.Column(db.String(64), primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=True)
    username = db.Column(db.String(64), nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联 - 指定外键以便正确建立关系
    scan_tasks = db.relationship('ScanTask', backref='user', lazy='dynamic',
                                  foreign_keys='ScanTask.user_id')