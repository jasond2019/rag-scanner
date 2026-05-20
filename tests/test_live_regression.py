"""
Live API Regression Tests
Tests against deployed Vercel endpoints
"""

import pytest
import requests
import time
import uuid
import os


# 默认 API URL（可通过环境变量覆盖）
API_URL = os.environ.get("API_URL", "https://rag-scanner.vercel.app")


class TestHealthAPI:
    """健康检查 API 测试"""

    def test_health_endpoint(self):
        """测试健康检查端点"""
        resp = requests.get(f"{API_URL}/api/health", timeout=30)
        assert resp.status_code == 200

        data = resp.json()
        assert data.get("code") == 0 or data.get("success") == True
        assert "status" in data.get("data", data)

    def test_health_database_status(self):
        """测试数据库状态检查"""
        resp = requests.get(f"{API_URL}/api/health", timeout=30)
        data = resp.json()

        health_data = data.get("data", data)
        checks = health_data.get("checks", {})

        # 数据库检查应该存在
        assert "database" in checks or "db" in checks


class TestCurlParser:
    """curl 解析测试"""

    def test_simple_url(self):
        """测试简单 URL 解析"""
        curl_cmd = "curl 'https://httpbin.org/post'"
        resp = requests.post(
            f"{API_URL}/api/scan/parse_curl",
            json={"curl": curl_cmd},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data.get("code") == 0
        assert "url" in data.get("data", {})
        assert data["data"]["url"] == "https://httpbin.org/post"

    def test_with_headers(self):
        """测试带 headers 的 curl"""
        curl_cmd = "curl 'https://api.example.com' -H 'Authorization: Bearer test123'"
        resp = requests.post(
            f"{API_URL}/api/scan/parse_curl",
            json={"curl": curl_cmd},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data.get("code") == 0
        headers = data.get("data", {}).get("headers", {})
        assert "Authorization" in headers

    def test_with_data(self):
        """测试带 POST data 的 curl"""
        curl_cmd = "curl 'https://api.example.com' -d '{\"query\":\"test\"}'"
        resp = requests.post(
            f"{API_URL}/api/scan/parse_curl",
            json={"curl": curl_cmd},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data.get("code") == 0
        param_name = data.get("data", {}).get("param_name", "")
        assert param_name in ("query", "prompt", "")

    def test_invalid_curl(self):
        """测试无效 curl 命令"""
        curl_cmd = "not a curl command"
        resp = requests.post(
            f"{API_URL}/api/scan/parse_curl",
            json={"curl": curl_cmd},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        # 无效输入返回 400 或 200（取决于 API 设计）
        assert resp.status_code in (200, 400)

        data = resp.json()
        # API 返回错误码
        assert data.get("code") == 1


class TestScanFlow:
    """完整扫描流程测试"""

    def test_submit_scan(self):
        """测试提交扫描任务"""
        user_id = f"regression_test_{uuid.uuid4().hex[:8]}"

        resp = requests.post(
            f"{API_URL}/api/scan/submit",
            json={
                "url": "https://httpbin.org/post",
                "input_type": "url",
                "user_id": user_id,
            },
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data.get("code") == 0
        assert "task_id" in data.get("data", {})

        # 保存 task_id 用于后续测试
        return data["data"]["task_id"]

    def test_execute_scan(self):
        """测试执行扫描"""
        # 先提交任务
        user_id = f"regression_test_{uuid.uuid4().hex[:8]}"
        submit_resp = requests.post(
            f"{API_URL}/api/scan/submit",
            json={
                "url": "https://httpbin.org/post",
                "input_type": "url",
                "user_id": user_id,
            },
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        task_id = submit_resp.json()["data"]["task_id"]

        # 执行扫描
        exec_resp = requests.post(
            f"{API_URL}/api/scan/execute",
            json={
                "task_id": task_id,
                "url": "https://httpbin.org/post",
                "headers": {},
                "param_name": "query",
            },
            headers={"Content-Type": "application/json"},
            timeout=60,  # 执行可能较慢
        )
        assert exec_resp.status_code == 200

        data = exec_resp.json()
        assert data.get("code") == 0

    def test_progress_query(self):
        """测试进度查询"""
        # 执行一次扫描
        user_id = f"regression_test_{uuid.uuid4().hex[:8]}"
        submit_resp = requests.post(
            f"{API_URL}/api/scan/submit",
            json={
                "url": "https://httpbin.org/post",
                "input_type": "url",
                "user_id": user_id,
            },
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        task_id = submit_resp.json()["data"]["task_id"]

        # 查询进度
        progress_resp = requests.get(
            f"{API_URL}/api/scan/progress?task_id={task_id}",
            timeout=30,
        )
        assert progress_resp.status_code == 200

        data = progress_resp.json()
        assert data.get("code") == 0
        assert "progress" in data.get("data", {})
        assert "status" in data.get("data", {})

    def test_result_query(self):
        """测试结果查询"""
        # 执行完整扫描
        user_id = f"regression_test_{uuid.uuid4().hex[:8]}"

        submit_resp = requests.post(
            f"{API_URL}/api/scan/submit",
            json={
                "url": "https://httpbin.org/post",
                "input_type": "url",
                "user_id": user_id,
            },
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        task_id = submit_resp.json()["data"]["task_id"]

        exec_resp = requests.post(
            f"{API_URL}/api/scan/execute",
            json={
                "task_id": task_id,
                "url": "https://httpbin.org/post",
                "headers": {},
                "param_name": "query",
            },
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        # 等待完成
        for _ in range(10):
            time.sleep(2)
            progress_resp = requests.get(
                f"{API_URL}/api/scan/progress?task_id={task_id}",
                timeout=30,
            )
            status = progress_resp.json().get("data", {}).get("status", "")
            if status in ("completed", "failed"):
                break

        # 查询结果
        result_resp = requests.get(
            f"{API_URL}/api/scan/result?task_id={task_id}",
            timeout=30,
        )
        assert result_resp.status_code == 200

        data = result_resp.json()
        assert data.get("code") == 0
        result_data = data.get("data", {})
        assert "score" in result_data
        assert "level" in result_data
        # score 应该是整数（不是 null）
        assert result_data["score"] is not None


class TestAdminAPI:
    """Admin API 测试"""

    def test_stats_endpoint(self):
        """测试统计端点"""
        resp = requests.get(f"{API_URL}/api/admin/stats", timeout=30)
        assert resp.status_code == 200

        data = resp.json()
        assert data.get("success") == True
        assert "total_tasks" in data.get("data", {})

    def test_tasks_endpoint(self):
        """测试任务列表端点"""
        resp = requests.get(f"{API_URL}/api/admin/tasks?limit=5", timeout=30)
        assert resp.status_code == 200

        data = resp.json()
        assert data.get("success") == True
        assert "tasks" in data.get("data", {})

    def test_history_endpoint(self):
        """测试历史记录端点"""
        # 使用固定 user_id 测试
        user_id = "regression_test_user"

        resp = requests.get(
            f"{API_URL}/api/admin/history?user_id={user_id}",
            timeout=30,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data.get("success") == True

    def test_history_missing_user(self):
        """测试缺少 user_id 的历史记录请求"""
        resp = requests.get(f"{API_URL}/api/admin/history", timeout=30)
        # 应该返回 400 或错误
        assert resp.status_code in (400, 200)  # 两种处理方式都可以


class TestScanEndpoint:
    """扫描根端点测试"""

    def test_scan_root(self):
        """测试 /api/scan 端点"""
        resp = requests.get(f"{API_URL}/api/scan", timeout=30)
        assert resp.status_code == 200

        data = resp.json()
        # 应该返回服务信息
        assert data.get("code") == 0 or data.get("name") is not None


def run_all_tests(api_url: str = None):
    """运行所有测试"""
    if api_url:
        global API_URL
        API_URL = api_url

    print(f"\n=== 回归测试 ===")
    print(f"API URL: {API_URL}")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 收集测试结果
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": [],
    }

    test_classes = [
        TestHealthAPI,
        TestCurlParser,
        TestScanFlow,
        TestAdminAPI,
        TestScanEndpoint,
    ]

    for test_class in test_classes:
        class_name = test_class.__name__
        print(f"\n[{class_name}]")

        instance = test_class()

        # 获取所有测试方法
        test_methods = [
            m for m in dir(instance) if m.startswith("test_") and callable(getattr(instance, m))
        ]

        for method_name in test_methods:
            results["total"] += 1
            try:
                method = getattr(instance, method_name)
                method()
                results["passed"] += 1
                print(f"  [PASS] {method_name}")
            except AssertionError as e:
                results["failed"] += 1
                results["errors"].append({
                    "class": class_name,
                    "method": method_name,
                    "error": str(e),
                })
                print(f"  [FAIL] {method_name}: {e}")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "class": class_name,
                    "method": method_name,
                    "error": str(e),
                })
                print(f"  [FAIL] {method_name}: {type(e).__name__}: {e}")

    # 输出汇总
    print(f"\n=== 测试汇总 ===")
    print(f"总数: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    if results["failed"] > 0:
        print("\n失败详情:")
        for err in results["errors"]:
            print(f"  - {err['class']}.{err['method']}: {err['error']}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="运行回归测试")
    parser.add_argument("--api-url", help="API URL（默认: https://rag-scanner.vercel.app）")

    args = parser.parse_args()

    results = run_all_tests(args.api_url)

    # 返回码：失败则返回 1
    exit(0 if results["failed"] == 0 else 1)