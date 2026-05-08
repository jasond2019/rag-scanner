"""
Vercel Postgres 数据库连接
支持 Neon Postgres 连接
"""

import os
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Neon 提供多种环境变量，优先使用 DATABASE_URL（推荐）
# 或 POSTGRES_URL（Vercel Postgres 模板）
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

engine = None
SessionLocal = None
db_error = None

if DATABASE_URL:
    try:
        # pg8000 是纯 Python 驱动，Vercel Serverless 兼容
        db_url = DATABASE_URL
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgresql+pg8000://', 1)

        engine = create_engine(db_url, pool_pre_ping=True, pool_size=1, max_overflow=0)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        print(f"Database engine created: {db_url[:30]}...")
    except Exception as e:
        db_error = str(e)
        print(f"Database engine creation failed: {e}")
else:
    db_error = "No DATABASE_URL or POSTGRES_URL found"
    print(f"Database URL not set. Available env vars: {list(os.environ.keys())}")


Base = declarative_base()


class ScanTask(Base):
    """扫描任务表"""
    __tablename__ = 'scan_tasks'

    id = Column(String(64), primary_key=True)
    target_type = Column(String(32), nullable=False)
    target_value = Column(Text, nullable=False)
    status = Column(String(32), default='queued')
    progress = Column(Integer, default=0)
    current_step = Column(String(64), default='waiting')
    score = Column(Integer, nullable=True)
    level = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Vulnerability(Base):
    """漏洞结果表"""
    __tablename__ = 'vulnerabilities'

    id = Column(String(64), primary_key=True)
    task_id = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    severity = Column(String(32), nullable=False)
    description = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)


def init_db():
    """初始化数据库表"""
    if engine:
        try:
            Base.metadata.create_all(bind=engine)
            return True
        except Exception as e:
            print(f"init_db error: {e}")
            return False
    return False


def get_session():
    """获取数据库会话"""
    if SessionLocal:
        try:
            return SessionLocal()
        except Exception as e:
            print(f"get_session error: {e}")
    return None


def get_db_status():
    """获取数据库状态（用于诊断）"""
    return {
        'database_url_set': bool(DATABASE_URL),
        'engine_created': bool(engine),
        'session_available': bool(SessionLocal),
        'db_error': db_error,
        'available_env_vars': [k for k in os.environ.keys() if 'DATABASE' in k or 'POSTGRES' in k or 'PG' in k]
    }