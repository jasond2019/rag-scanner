# RAG Scanner

[中文文档](README_CN.md)

A lightweight RAG system security scanner with one-click detection of 10 security vulnerabilities.

**Online Access**: https://jasond2019.github.io/rag-scanner

## Features

- **Postman-style Interaction** - Paste curl commands or URLs directly
- **10 Security Checks** - Prompt injection, data leakage, vector injection, etc.
- **HTTP Polling Progress** - Real-time scan progress updates
- **PDF Report Generation** - Professional security assessment reports

## Architecture

```
GitHub Pages (Frontend) → Vercel Serverless API (Backend)
                              ↓
                        Vercel Postgres (Database)
                        Vercel KV (Progress Cache)
                        Vercel Blob (PDF Reports)
```

## Deployment

### Vercel Backend

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Create Storage (in Vercel dashboard):
# - Vercel Postgres
# - Vercel KV
# - Vercel Blob
```

### GitHub Pages Frontend

1. Push `frontend/` directory to GitHub
2. Enable GitHub Pages in repo settings
3. Set source to `frontend` folder

## Quick Start

### Local Development

### Installation

```bash
# Clone repository
git clone https://github.com/JasonD2019/rag-scanner.git
cd rag-scanner

# Install dependencies
pip install -r requirements.txt
```

### Launch

```bash
# Development mode
python main.py

# Or use startup scripts
./start.sh  # Linux/Mac
start.bat   # Windows
```

Visit http://localhost:5000

### Usage

**Method 1: Paste curl Command (Recommended)**

Browser F12 → Network → Right-click request → Copy as cURL → Paste into scanner

```
curl 'https://api.example.com/chat' \
  -H 'Authorization: Bearer sk-xxx' \
  -d '{"query":"hello"}'
```

The curl command is automatically parsed:
- URL
- Authentication info (Authorization / API Key)
- Parameter name

**Method 2: Paste URL + Manual Config**

Enter URL, manually select parameter name and input auth token

```
https://api.example.com/chat
```

## 10 Security Checks

| Check | Description | Risk Level |
|-------|-------------|------------|
| Prompt Injection | Prompt Injection attack detection | High |
| Data Leakage | Sensitive path access detection | High |
| Vector Injection | Vector DB injection attack | High |
| Retrieval Pollution | Retrieval Pollution detection | High |
| Auth Bypass | Authentication bypass detection | Medium |
| API Abuse | Rate Limit / Abuse detection | Medium |
| Log Leakage | Log Information Leakage | Medium |
| Model Jailbreak | Model Jailbreak detection | Medium |
| Dependency Vulnerability | Dependency vulnerability scan | Low |
| Configuration Error | Configuration error detection | Low |

## Rules Library

Built-in [ragshield-rules](https://github.com/JasonD2019/ragshield-rules) rules library:

- Injection rules (200+ patterns)
- Jailbreak rules (100+ patterns)
- Privacy rules (14 regex)
- Sensitive content rules (50+ patterns)

## Project Structure

```
rag-scanner/
├── app/
│   ├── routes/              # API routes
│   ├── services/            # Business services
│   └── templates/           # Web UI
├── scanner/
│   ├── engine.py            # Scan engine
│   ├── scorer.py            # Scoring system
│   ├── detectors/           # 10 detectors
│   └── rules/               # Rules library
├── tests/                   # Test files
├── wordlists/               # Dictionary files
├── requirements.txt
└── Dockerfile
```

## Docker Deployment

```bash
# Build image
docker build -t rag-scanner .

# Use docker-compose
docker-compose up -d
```

## API Documentation

### Parse curl Command

```http
POST /api/v1/scan/parse-curl
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

### Submit Scan Task

```http
POST /api/v1/scan/submit
Content-Type: application/json

{
  "target_value": "curl ...",  // or URL
  "param_name": "query"        // optional, override parsed result
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

### Get Scan Result

```http
GET /api/v1/scan/{task_id}/result

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

## Security Scoring Algorithm

```
Base Score: 100 points
Deduction Rules:
- High-risk vulnerability: -15 points each
- Medium-risk vulnerability: -10 points each
- Low-risk vulnerability: -5 points each

Risk Levels:
- High Risk: 0-59 points
- Medium Risk: 60-79 points
- Low Risk: 80-100 points
```

## Update Rules Library

```bash
# Get latest rules from ragshield-rules
git clone https://github.com/JasonD2019/ragshield-rules.git temp-rules
cp -r temp-rules/* scanner/rules/
rm -rf temp-rules
```

## Related Projects

| Project | Description |
|---------|-------------|
| [ragshield-rules](https://github.com/JasonD2019/ragshield-rules) | Rules library |
| [raguard-sdk](https://github.com/JasonD2019/raguard-sdk) | Python SDK |

## License

MIT License

## Contributing

Issues and Pull Requests are welcome!