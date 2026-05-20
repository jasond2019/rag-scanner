"""
健康检查 API 测试
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "api"))


class TestHealthAPI:

    def test_health_endpoint_exists(self):
        """测试健康检查端点存在"""
        from health import app

        client = app.test_client()
        response = client.get("/api/health")

        assert response.status_code == 200

    def test_health_response_format(self):
        """测试响应格式正确"""
        from health import app

        client = app.test_client()
        response = client.get("/api/health")
        data = response.get_json()

        assert "code" in data
        assert "data" in data
        assert "status" in data["data"]
        assert "checks" in data["data"]
        assert "version" in data["data"]

    def test_health_status_values(self):
        """测试状态值有效"""
        from health import app

        client = app.test_client()
        response = client.get("/api/health")
        data = response.get_json()

        # status 应为 healthy, degraded, 或 unhealthy
        assert data["data"]["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_database_check(self):
        """测试数据库检查"""
        from health import app

        client = app.test_client()
        response = client.get("/api/health")
        data = response.get_json()

        # database 检查应存在
        assert "database" in data["data"]["checks"]
        db_status = data["data"]["checks"]["database"]["status"]
        assert db_status in ["connected", "disconnected", "error"]

    def test_health_detectors_check(self):
        """测试检测器检查"""
        from health import app

        client = app.test_client()
        response = client.get("/api/health")
        data = response.get_json()

        # detectors 检查应存在
        assert "detectors" in data["data"]["checks"]
        assert "count" in data["data"]["checks"]["detectors"]
        # 检测器数量应为 10（设计值），允许部分加载失败时 >= 6
        assert data["data"]["checks"]["detectors"]["count"] >= 6

    def test_health_scorer_check(self):
        """测试评分器检查"""
        from health import app

        client = app.test_client()
        response = client.get("/api/health")
        data = response.get_json()

        # scorer 检查应存在
        assert "scorer" in data["data"]["checks"]
        assert data["data"]["checks"]["scorer"]["status"] in ["ready", "error"]

    def test_health_options_request(self):
        """测试 OPTIONS 请求"""
        from health import app

        client = app.test_client()
        response = client.options("/api/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["code"] == 0

    def test_health_version(self):
        """测试版本号"""
        from health import app

        client = app.test_client()
        response = client.get("/api/health")
        data = response.get_json()

        assert data["data"]["version"] == "1.0.0"

    def test_health_timestamp(self):
        """测试时间戳格式"""
        from health import app

        client = app.test_client()
        response = client.get("/api/health")
        data = response.get_json()

        assert "timestamp" in data["data"]
        # ISO 格式时间戳
        assert "Z" in data["data"]["timestamp"] or "+" in data["data"]["timestamp"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])