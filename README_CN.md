# RAG Scanner

[English](README.md)

🛡️ 一款轻量级 RAG 系统安全扫描工具，支持一键检测 10 项安全漏洞。

## 功能特性

- **Postman 风格交互** - 支持直接粘贴 curl 命令或 URL
- **10 项安全检测** - 提示词注入、数据泄露、向量注入等
- **实时进度展示** - WebSocket 推送扫描进度
- **PDF 报告生成** - 专业安全评估报告

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/JasonD2019/rag-scanner.git
cd rag-scanner

# 安装依赖
pip install -r requirements.txt
```

### 启动

```bash
# 开发模式
python main.py

# 或使用启动脚本
./start.sh  # Linux/Mac
start.bat   # Windows
```

访问 http://localhost:5000

### 使用方式

**方式 1：粘贴 curl 命令（推荐）**

浏览器 F12 → Network → 右键请求 → Copy as cURL → 粘贴到扫描器

```
curl 'https://api.example.com/chat' \
  -H 'Authorization: Bearer sk-xxx' \
  -d '{"query":"hello"}'
```

curl 命令会自动解析：
- URL
- 认证信息（Authorization / API Key）
- 参数名

**方式 2：粘贴 URL + 手动配置**

输入 URL，手动选择参数名和输入认证 Token

```
https://api.example.com/chat
```

## 10 项安全检测

| 检测项 | 说明 | 风险等级 |
|--------|------|----------|
| 提示词注入 | Prompt Injection 攻击检测 | 高危 |
| 数据泄露 | 敏感路径访问检测 | 高危 |
| 向量库注入 | Vector DB 注入攻击 | 高危 |
| 检索污染 | Retrieval Pollution 检测 | 高危 |
| 权限绕过 | Auth Bypass 检测 | 中危 |
| API 滥用 | Rate Limit / Abuse 检测 | 中危 |
| 日志泄露 | Log Information Leakage | 中危 |
| 模型越狱 | Model Jailbreak 检测 | 中危 |
| 依赖漏洞 | Dependency Vulnerability | 低危 |
| 配置错误 | Configuration Error | 低危 |

## 规则库

本项目内置 [ragshield-rules](https://github.com/JasonD2019/ragshield-rules) 规则库：

- 注入检测规则 (200+ 模式)
- 越狱检测规则 (100+ 模式)
- 隐私检测规则 (14 正则)
- 敏感内容规则 (50+ 模式)

## 项目结构

```
rag-scanner/
├── app/
│   ├── routes/              # API 路由
│   ├── services/            # 业务服务
│   └── templates/           # Web UI
├── scanner/
│   ├── engine.py            # 扫描引擎
│   ├── scorer.py            # 评分系统
│   ├── detectors/           # 10 个检测器
│   └── rules/               # 规则库
├── tests/                   # 测试文件
├── wordlists/               # 字典文件
├── requirements.txt
└── Dockerfile
```

## Docker 部署

```bash
# 构建镜像
docker build -t rag-scanner .

# 使用 docker-compose
docker-compose up -d
```

## API 文档

### 解析 curl 命令

```http
POST /api/scan/parse_curl
Content-Type: application/json

{
  "curl": "curl 'https://api.example.com' -H 'Authorization: Bearer xxx' -d '{\"query\":\"test\"}'"
}

Response:
{
  "code": 0,
  "data": {
    "url": "https://api.example.com",
    "method": "POST",
    "param_name": "query",
    "auth_header": "Bearer xxx..."
  }
}
```

### 提交扫描任务

```http
POST /api/scan/submit
Content-Type: application/json

{
  "target_value": "curl ...",  // 或 URL
  "param_name": "query"        // 可选，覆盖解析结果
}

Response:
{
  "code": 0,
  "data": {
    "task_id": "scan_20260101_120000_abc123",
    "status": "queued"
  }
}
```

### 查询扫描进度

```http
GET /api/scan/progress?task_id=xxx

Response:
{
  "code": 0,
  "data": {
    "task_id": "scan_xxx",
    "status": "running",
    "progress": 45,
    "current_step": "提示词注入检测"
  }
}
```

### 执行扫描

```http
POST /api/scan/execute
Content-Type: application/json

{
  "task_id": "scan_xxx",
  "url": "https://api.example.com",
  "headers": {"Authorization": "Bearer xxx"},
  "param_name": "query"
}

Response:
{
  "code": 0,
  "data": {
    "score": 85,
    "level": "medium",
    "vulnerabilities": [...]
  }
}
```

### 获取扫描结果

```http
GET /api/scan/result?task_id=xxx

Response:
{
  "code": 0,
  "data": {
    "score": 85,
    "level": "medium",
    "vulnerabilities": [...]
  }
}
```

## 安全评分算法

```
基础分: 100 分
扣分规则:
- 高危漏洞: -15 分/个
- 中危漏洞: -10 分/个
- 低危漏洞: -5 分/个

风险等级:
- 高风险: 0-59 分
- 中风险: 60-79 分
- 低风险: 80-100 分
```

## 规则库更新

```bash
# 从 ragshield-rules 获取最新规则
git clone https://github.com/JasonD2019/ragshield-rules.git temp-rules
cp -r temp-rules/* scanner/rules/
rm -rf temp-rules
```

## 相关项目

| 项目 | 说明 |
|------|------|
| [ragshield-rules](https://github.com/JasonD2019/ragshield-rules) | 规则库 |
| [raguard-sdk](https://github.com/JasonD2019/raguard-sdk) | Python SDK |

## License

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！