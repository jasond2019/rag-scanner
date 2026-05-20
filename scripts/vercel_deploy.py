"""
Vercel Deployment Checker
Wait for deployment to complete before running tests
"""

import os
import time
import requests
import json
from datetime import datetime


class VercelDeploymentChecker:
    """检查 Vercel 部署状态"""

    API_URL = "https://api.vercel.com"

    def __init__(self, project_id: str = None, token: str = None):
        self.project_id = project_id or os.environ.get("VERCEL_PROJECT_ID")
        self.token = token or os.environ.get("VERCEL_TOKEN")

        if not self.project_id:
            raise ValueError("需要 VERCEL_PROJECT_ID 环境变量")
        if not self.token:
            raise ValueError("需要 VERCEL_TOKEN 环境变量")

    def get_latest_deployment(self) -> dict:
        """获取最新部署"""
        url = f"{self.API_URL}/v13/deployments"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"projectId": self.project_id, "limit": 1}

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        deployments = data.get("deployments", [])
        if not deployments:
            return None

        return deployments[0]

    def get_deployment_status(self, deployment_id: str) -> dict:
        """获取特定部署状态"""
        url = f"{self.API_URL}/v13/deployments/{deployment_id}"
        headers = {"Authorization": f"Bearer {self.token}"}

        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def wait_for_deployment(
        self,
        max_wait: int = 300,
        poll_interval: int = 10,
        target_state: str = "READY",
    ) -> dict:
        """
        等待部署完成

        Args:
            max_wait: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）
            target_state: 目标状态（READY, ERROR, CANCELED）

        Returns:
            部署信息字典
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始检查 Vercel 部署状态...")

        # 获取最新部署
        deployment = self.get_latest_deployment()
        if not deployment:
            raise RuntimeError("未找到任何部署记录")

        deployment_id = deployment["uid"]
        current_state = deployment.get("state", "UNKNOWN")
        production_url = deployment.get("targets", {}).get("production", {}).get("url", "")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 最新部署 ID: {deployment_id}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 当前状态: {current_state}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 生产 URL: {production_url}")

        # 如果已经完成，直接返回
        if current_state == target_state:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 部署已完成！")
            return deployment

        # 等待部署完成
        start_time = time.time()
        while time.time() - start_time < max_wait:
            time.sleep(poll_interval)

            deployment = self.get_deployment_status(deployment_id)
            current_state = deployment.get("state", "UNKNOWN")

            elapsed = int(time.time() - start_time)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 状态: {current_state} (已等待 {elapsed}s)")

            if current_state == target_state:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ 部署成功完成！")
                return deployment

            if current_state in ("ERROR", "CANCELED"):
                raise RuntimeError(f"部署失败: {current_state}")

        raise RuntimeError(f"等待超时 ({max_wait}s)，部署状态: {current_state}")

    def trigger_deployment(self) -> dict:
        """触发新部署"""
        url = f"{self.API_URL}/v13/deployments"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        data = {"projectId": self.project_id}

        resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="检查 Vercel 部署状态")
    parser.add_argument("--project-id", help="Vercel 项目 ID")
    parser.add_argument("--token", help="Vercel API Token")
    parser.add_argument("--max-wait", type=int, default=300, help="最大等待时间（秒）")
    parser.add_argument("--trigger", action="store_true", help="触发新部署")

    args = parser.parse_args()

    checker = VercelDeploymentChecker(args.project_id, args.token)

    if args.trigger:
        print("触发新部署...")
        deployment = checker.trigger_deployment()
        print(f"部署 ID: {deployment['uid']}")

    deployment = checker.wait_for_deployment(max_wait=args.max_wait)

    # 输出部署信息
    print("\n=== 部署信息 ===")
    print(f"ID: {deployment['uid']}")
    print(f"状态: {deployment['state']}")
    print(f"URL: {deployment.get('targets', {}).get('production', {}).get('url', '')}")
    print(f"创建时间: {deployment.get('createdAt', '')}")

    return deployment


if __name__ == "__main__":
    main()