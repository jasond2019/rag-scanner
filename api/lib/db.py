"""
Vercel Postgres 数据库连接
使用 pg8000 纯 Python 驱动（Vercel Serverless 兼容）
"""

import os
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Vercel Postgres 环境变量
POSTGRES_URL = os.environ.get('POSTGRES_URL')

engine = None
SessionLocal = None

if POSTGRES_URL:
    try:
        # pg8000 驱动，替换 postgresql:// 为 postgresql+pg8000://
        db_url = POSTGRES_URL
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgresql+pg8000://', 1)

        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        print(f"Database engine created successfully")
    except Exception as e:
        print(f"Database engine creation failed: {e}")
else:
    print("POSTGRES_URL not set, using fallback mode")

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
            print("Database tables created/verified")
        except Exception as e:
            print(f"init_db error: {e}")


def get_session():
    """获取数据库会话"""
    if SessionLocal:
        try:
            return SessionLocal()
        except Exception as e:
            print(f"get_session error: {e}")
    return None