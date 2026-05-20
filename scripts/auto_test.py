"""
自动化部署测试脚本

流程：
1. 等待 Vercel 部署完成（可选）
2. 运行完整回归测试
3. 输出测试报告

使用方法：
  python scripts/auto_test.py                  # 直接测试（使用默认 URL）
  python scripts/auto_test.py --wait-deploy    # 等待部署完成后测试
  python scripts/auto_test.py --api-url URL    # 测试指定 URL
"""

import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tests"))

from tests.test_live_regression import run_all_tests


def wait_for_vercel_deployment(max_wait: int = 300) -> str:
    """
    等待 Vercel 部署完成

    Returns:
        部署完成后的 API URL
    """
    from scripts.vercel_deploy import VercelDeploymentChecker

    print("\n=== 等待 Vercel 部署 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    checker = VercelDeploymentChecker()
    deployment = checker.wait_for_deployment(max_wait=max_wait)

    # 获取生产 URL
    targets = deployment.get("targets", {})
    production = targets.get("production", {})
    api_url = production.get("url", "")

    if api_url:
        # 确保 URL 格式正确
        api_url = f"https://{api_url}" if not api_url.startswith("http") else api_url
    else:
        # 使用默认 URL
        api_url = "https://rag-scanner.vercel.app"

    print(f"部署完成，API URL: {api_url}")
    return api_url


def run_regression_tests(api_url: str) -> dict:
    """
    运行回归测试

    Args:
        api_url: API URL

    Returns:
        测试结果字典
    """
    print("\n=== 运行回归测试 ===")
    print(f"API URL: {api_url}")

    results = run_all_tests(api_url)
    return results


def generate_report(results: dict, api_url: str, output_file: str = None) -> str:
    """
    生成测试报告

    Args:
        results: 测试结果
        api_url: API URL
        output_file: 报告输出文件路径（可选）

    Returns:
        报告内容
    """
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("RAG Scanner 自动化测试报告")
    report_lines.append("=" * 60)
    report_lines.append("")
    report_lines.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"API URL: {api_url}")
    report_lines.append("")
    report_lines.append("-" * 60)
    report_lines.append("测试汇总")
    report_lines.append("-" * 60)
    report_lines.append(f"总测试数: {results['total']}")
    report_lines.append(f"通过: {results['passed']}")
    report_lines.append(f"失败: {results['failed']}")
    pass_rate = results['passed'] / results['total'] * 100 if results['total'] > 0 else 0
    report_lines.append(f"通过率: {pass_rate:.1f}%")
    report_lines.append("")

    if results["failed"] > 0:
        report_lines.append("-" * 60)
        report_lines.append("失败详情")
        report_lines.append("-" * 60)
        for err in results["errors"]:
            report_lines.append(f"  {err['class']}.{err['method']}")
            report_lines.append(f"    错误: {err['error']}")
        report_lines.append("")

    report_lines.append("=" * 60)
    status = "成功" if results["failed"] == 0 else "失败"
    report_lines.append(f"测试状态: {status}")
    report_lines.append("=" * 60)

    report = "\n".join(report_lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存到: {output_file}")

    return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="自动化部署测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/auto_test.py                     # 直接测试默认 URL
  python scripts/auto_test.py --wait-deploy       # 等待 Vercel 部署后测试
  python scripts/auto_test.py --api-url https://xxx.vercel.app
  python scripts/auto_test.py --report report.txt --wait-deploy
        """
    )

    parser.add_argument(
        "--wait-deploy",
        action="store_true",
        help="等待 Vercel 部署完成后再测试",
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=300,
        help="等待部署的最大时间（秒），默认 300",
    )
    parser.add_argument(
        "--api-url",
        help="指定 API URL（不等待部署）",
    )
    parser.add_argument(
        "--report",
        help="报告输出文件路径",
    )

    args = parser.parse_args()

    # 确定 API URL
    if args.api_url:
        api_url = args.api_url
    elif args.wait_deploy:
        try:
            api_url = wait_for_vercel_deployment(max_wait=args.max_wait)
        except Exception as e:
            print(f"\n❌ 等待部署失败: {e}")
            sys.exit(1)
    else:
        api_url = os.environ.get("API_URL", "https://rag-scanner.vercel.app")

    # 运行测试
    try:
        results = run_regression_tests(api_url)
    except Exception as e:
        print(f"\n❌ 运行测试失败: {e}")
        sys.exit(1)

    # 生成报告
    report = generate_report(results, api_url, args.report)
    print("\n" + report)

    # 返回码
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()