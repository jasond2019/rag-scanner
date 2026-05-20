@echo off
REM RAG Scanner 自动化测试脚本
REM 使用方法: 运行此脚本等待 Vercel 部署完成后执行回归测试

echo ========================================
echo RAG Scanner 自动化部署测试
echo ========================================
echo.

REM 检查环境变量
if "%VERCEL_TOKEN%"=="" (
    echo 警告: VERCEL_TOKEN 未设置
    echo 请设置环境变量: set VERCEL_TOKEN=your_token
    echo.
)

if "%VERCEL_PROJECT_ID%"=="" (
    echo 警告: VERCEL_PROJECT_ID 未设置
    echo 请设置环境变量: set VERCEL_PROJECT_ID=your_project_id
    echo.
)

REM 运行自动化测试
python scripts/auto_test.py --wait-deploy --report test_report.txt

echo.
echo 测试完成！查看 test_report.txt 获取详细报告。