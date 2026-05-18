"""
API 端点集成测试
"""

import pytest
import sys
import os
from pathlib import Path

# 添加 api 目录到 Python 路径
api_dir = Path(__file__).parent.parent / "api"
sys.path.insert(0, str(api_dir))


class TestDatabaseConnection:
    """数据库连接测试"""

    def test_db_init(self):
        """测试数据库初始化"""
        from lib.db import init_db, engine, DATABASE_URL

        # 本地测试可能没有数据库连接
        if not DATABASE_URL:
            pytest.skip("Database URL not set (local test)")

        result = init_db()
        assert result is True or engine is not None

    def test_db_session(self):
        """测试数据库会话"""
        from lib.db import get_session, DATABASE_URL

        # 本地测试可能没有数据库连接
        if not DATABASE_URL:
            pytest.skip("Database URL not set (local test)")

        db = get_session()
        if db:
            db.close()
            assert True
        else:
            pytest.skip("Database session not available")


class TestScanTaskModel:
    """扫描任务模型测试"""

    def test_task_creation(self, test_db):
        """测试任务创建"""
        if not test_db:
            pytest.skip("Database not available")

        from lib.db import ScanTask

        task = ScanTask(
            id="test_create_001",
            target_type="url",
            target_value="https://test.com",
            status="queued",
            progress=0
        )
        test_db.add(task)
        test_db.commit()

        # 查询验证
        saved = test_db.query(ScanTask).filter(ScanTask.id == "test_create_001").first()
        assert saved is not None
        assert saved.target_value == "https://test.com"

        # 清理
        test_db.delete(saved)
        test_db.commit()

    def test_task_progress_update(self, sample_task):
        """测试任务进度更新"""
        if not sample_task:
            pytest.skip("Database not available")

        from lib.db import get_session

        db = get_session()
        if not db:
            pytest.skip("Database not available")

        task = db.query(type(sample_task)).filter_by(id=sample_task.id).first()
        if task:
            task.progress = 50
            task.status = "running"
            task.current_step = "提示词注入检测"
            db.commit()

            # 验证更新
            updated = db.query(type(sample_task)).filter_by(id=sample_task.id).first()
            assert updated.progress == 50
            assert updated.status == "running"

        db.close()


class TestVulnerabilityModel:
    """漏洞模型测试"""

    def test_vulnerability_creation(self, completed_task):
        """测试漏洞创建"""
        if not completed_task:
            pytest.skip("Database not available")

        from lib.db import get_session, Vulnerability

        db = get_session()
        if not db:
            pytest.skip("Database not available")

        vulns = db.query(Vulnerability).filter(Vulnerability.task_id == completed_task.id).all()
        assert len(vulns) >= 1
        assert vulns[0].severity == "high"

        db.close()


class TestProgressAPI:
    """进度 API 测试"""

    def test_progress_query(self, sample_task):
        """测试进度查询"""
        if not sample_task:
            pytest.skip("Database not available")

        from lib.db import get_session, ScanTask

        db = get_session()
        if not db:
            pytest.skip("Database not available")

        task = db.query(ScanTask).filter(ScanTask.id == sample_task.id).first()
        assert task is not None
        assert task.status == "queued"
        assert task.progress == 0

        db.close()

    def test_progress_completed(self, completed_task):
        """测试已完成任务进度"""
        if not completed_task:
            pytest.skip("Database not available")

        from lib.db import get_session, ScanTask

        db = get_session()
        if not db:
            pytest.skip("Database not available")

        task = db.query(ScanTask).filter(ScanTask.id == completed_task.id).first()
        assert task.status == "completed"
        assert task.progress == 100
        assert task.score == 85
        assert task.level == "medium"

        db.close()


class TestResultAPI:
    """结果 API 测试"""

    def test_result_query(self, completed_task):
        """测试结果查询"""
        if not completed_task:
            pytest.skip("Database not available")

        from lib.db import get_session, ScanTask, Vulnerability

        db = get_session()
        if not db:
            pytest.skip("Database not available")

        task = db.query(ScanTask).filter(ScanTask.id == completed_task.id).first()
        assert task.score == 85

        # 统计漏洞
        vuln_count = db.query(Vulnerability).filter(
            Vulnerability.task_id == completed_task.id
        ).count()
        assert vuln_count >= 1

        db.close()


class TestInvalidTaskId:
    """无效任务 ID 测试"""

    def test_invalid_task_id(self, test_db):
        """测试无效 task_id 查询"""
        if not test_db:
            pytest.skip("Database not available")

        from lib.db import get_session, ScanTask

        db = get_session()
        if not db:
            pytest.skip("Database not available")

        task = db.query(ScanTask).filter(ScanTask.id == "invalid_id_12345").first()
        assert task is None

        db.close()