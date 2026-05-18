"""
pytest fixtures for integration tests
"""

import pytest
import sys
import os
from pathlib import Path

# 添加 api 目录到 Python 路径
api_dir = Path(__file__).parent.parent / "api"
sys.path.insert(0, str(api_dir))


@pytest.fixture
def test_db():
    """测试数据库 fixture"""
    from lib.db import init_db, get_session, ScanTask, DATABASE_URL

    # 本地测试可能没有数据库连接
    if not DATABASE_URL:
        yield None
        return

    init_db()
    db = get_session()

    yield db

    # 清理测试数据
    if db:
        try:
            db.query(ScanTask).filter(ScanTask.id.like('test_%')).delete()
            db.commit()
        except:
            pass
        db.close()


@pytest.fixture
def sample_task(test_db):
    """创建测试任务"""
    if not test_db:
        yield None
        return

    from lib.db import ScanTask

    task = ScanTask(
        id="test_task_001",
        target_type="url",
        target_value="https://example.com/api",
        status="queued",
        progress=0,
        current_step="waiting"
    )
    test_db.add(task)
    test_db.commit()

    yield task

    # 清理
    try:
        test_db.query(ScanTask).filter(ScanTask.id == task.id).delete()
        test_db.commit()
    except:
        pass


@pytest.fixture
def completed_task(test_db):
    """创建已完成的测试任务"""
    if not test_db:
        yield None
        return

    from lib.db import ScanTask, Vulnerability
    import json
    from datetime import datetime

    task = ScanTask(
        id="test_completed_001",
        target_type="url",
        target_value="https://example.com/api",
        status="completed",
        progress=100,
        current_step="扫描完成",
        score=85,
        level="medium",
        completed_at=datetime.utcnow()
    )
    test_db.add(task)
    test_db.commit()

    # 添加漏洞
    vuln = Vulnerability(
        id="test_vuln_001",
        task_id=task.id,
        rule_id="prompt_injection",
        name="提示词注入漏洞",
        severity="high",
        score_deduction=10,
        description="检测到提示词注入风险",
        suggestion="加强输入过滤",
        evidence=json.dumps(["payload: 'Ignore previous instructions'"])
    )
    test_db.add(vuln)
    test_db.commit()

    yield task

    # 清理
    try:
        test_db.query(Vulnerability).filter(Vulnerability.task_id == task.id).delete()
        test_db.query(ScanTask).filter(ScanTask.id == task.id).delete()
        test_db.commit()
    except:
        pass


@pytest.fixture
def mock_request_data():
    """模拟请求数据"""
    return {
        "target_value": "https://api.example.com/chat",
        "target_type": "url",
        "param_name": "query",
        "headers": {"Authorization": "Bearer test-token"}
    }


@pytest.fixture
def mock_curl_command():
    """模拟 curl 命令"""
    return "curl 'https://api.example.com/chat' -H 'Authorization: Bearer test-token' -d '{\"query\":\"hello\"}'"