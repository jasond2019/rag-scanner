"""
Vercel Postgres 数据库连接
使用 SQLAlchemy 连接 Vercel Postgres (Neon)
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Vercel Postgres 环境变量
POSTGRES_URL = os.environ.get('POSTGRES_URL')

if POSTGRES_URL:
    engine = create_engine(
        POSTGRES_URL,
        pool_pre_ping=True,  # 检查连接是否有效
        pool_size=5,
        max_overflow=10
    )
else:
    # 本地开发 fallback
    engine = create_engine('sqlite:///./local_dev.db')

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    from lib.models import ScanTask, Vulnerability, ScoreBreakdown, ScanAuditLog
    Base.metadata.create_all(bind=engine)