# Changelog

All notable changes to RAG Scanner will be documented in this file.

## [1.0.0] - 2026-05-06

### Added
- Postman 风格输入交互，支持粘贴 curl 命令或 URL
- curl 命令自动解析（URL、认证、参数名）
- 参数名下拉选择 + 自定义输入
- 实时解析预览展示
- 10 项安全检测框架
- WebSocket 实时进度推送
- PDF 报告生成
- `/api/v1/scan/parse-curl` API 端点

### Security Detection
- 提示词注入检测 (Prompt Injection)
- 数据泄露检测 (Data Leak)
- 权限绕过检测 (Auth Bypass)
- 配置错误检测 (Config Check)

### Technical
- Flask + SocketIO 架构
- SQLite 数据持久化
- Docker 部署支持
- 审计日志记录

## [0.1.0] - 2026-04-07

### Added
- 项目骨架搭建
- 扫描引擎核心设计
- 评分系统设计
- 前端 UI 基础版