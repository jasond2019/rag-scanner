"""
curl 命令解析器
将 curl 命令转换为可用的请求格式配置
"""

import re
import json
from typing import Dict, Optional, List


class CurlParser:
    """curl 命令解析器"""

    # 常见参数名优先级
    COMMON_PARAMS = ["query", "prompt", "message", "input", "question", "text", "content"]

    # 系统字段（不作为主要参数名）
    SKIP_FIELDS = ["session_id", "token", "auth", "api_key", "user_id", "id", "timestamp", "version"]

    def parse(self, curl_cmd: str) -> Dict:
        """
        解析 curl 命令

        Args:
            curl_cmd: curl 命令字符串

        Returns:
            {
                "url": "http://...",
                "method": "POST",
                "headers": {"Content-Type": "application/json", ...},
                "body": {"query": "hello", ...},
                "body_raw": '{"query":"hello"}',
                "param_name": "query",
                "extra_params": {},
            }
        """

        result = {
            "url": None,
            "method": "GET",
            "headers": {},
            "body": None,
            "body_raw": None,
            "param_name": None,
            "extra_params": {},
        }

        # 清理命令
        cmd = curl_cmd.strip()

        # 处理多行 curl (移除反斜杠换行)
        cmd = cmd.replace("\\\n", " ").replace("\\\r\n", " ")
        cmd = re.sub(r'\\\s+', ' ', cmd)

        # 使用 shlex 分割参数
        try:
            import shlex
            tokens = shlex.split(cmd)
        except ValueError:
            # shlex 失败时使用简单分割
            tokens = self._simple_split(cmd)

        # 解析参数
        i = 1  # 跳过 'curl'
        while i < len(tokens):
            token = tokens[i]

            # -X / --request METHOD
            if token in ["-X", "--request"]:
                if i + 1 < len(tokens):
                    result["method"] = tokens[i + 1].upper()
                i += 2

            # -H / --header HEADER
            elif token in ["-H", "--header"]:
                if i + 1 < len(tokens):
                    header = tokens[i + 1]
                    if ":" in header:
                        key, value = header.split(":", 1)
                        result["headers"][key.strip()] = value.strip()
                i += 2

            # -d / --data / --data-raw / --data-binary
            elif token in ["-d", "--data", "--data-raw", "--data-binary"]:
                if i + 1 < len(tokens):
                    body_raw = tokens[i + 1]
                    result["body_raw"] = body_raw

                    # 尝试解析 JSON
                    try:
                        result["body"] = json.loads(body_raw)
                        result["param_name"] = self._extract_param_name(result["body"])
                        result["extra_params"] = self._extract_extra_params(result["body"], result["param_name"])
                    except json.JSONDecodeError:
                        # shlex 可能去掉了引号，尝试修复
                        try:
                            # 重新添加引号
                            fixed_body = self._fix_json_quotes(body_raw)
                            result["body"] = json.loads(fixed_body)
                            result["param_name"] = self._extract_param_name(result["body"])
                            result["extra_params"] = self._extract_extra_params(result["body"], result["param_name"])
                        except:
                            # 不是 JSON，保持原始格式
                            result["body"] = None
                i += 2

            # --location / -L (跟随重定向，忽略)
            elif token in ["-L", "--location", "--location-trusted"]:
                i += 1

            # --compressed (忽略)
            elif token == "--compressed":
                i += 1

            # -k / --insecure (忽略 SSL 验证，忽略)
            elif token in ["-k", "--insecure"]:
                i += 1

            # -s / --silent (静默模式，忽略)
            elif token in ["-s", "--silent"]:
                i += 1

            # URL (不以 - 开头的参数)
            elif not token.startswith("-") and not token.startswith("--"):
                # 检查是否是 URL
                if token.startswith("http://") or token.startswith("https://"):
                    result["url"] = token
                elif re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', token):
                    # 可能是域名，添加 http://
                    result["url"] = "http://" + token
                i += 1

            # 其他参数跳过
            else:
                i += 1

        # 验证必要字段
        if not result["url"]:
            raise ValueError("No URL found in curl command")

        # 如果没有指定 method 但有 body，默认 POST
        if result["body_raw"] and result["method"] == "GET":
            result["method"] = "POST"

        # 如果没有 Content-Type header 且有 body，添加默认
        if result["body"] and "Content-Type" not in result["headers"]:
            result["headers"]["Content-Type"] = "application/json"

        # 如果没有 param_name，使用默认
        if not result["param_name"]:
            result["param_name"] = "query"

        return result

    def _fix_json_quotes(self, body_raw: str) -> str:
        """
        修复 shlex 去掉的 JSON 引号

        例如: {target_value: http://test.com} -> {"target_value": "http://test.com"}
        """
        import re

        # 如果已经有引号，直接返回
        if '"' in body_raw or "'" in body_raw:
            return body_raw

        # 简单的 JSON 格式修复
        # 匹配 key: value 格式并添加引号
        fixed = body_raw.strip()

        # 处理对象格式 {key: value, key2: value2}
        if fixed.startswith('{') and fixed.endswith('}'):
            # 提取内容
            content = fixed[1:-1].strip()

            # 分割键值对
            pairs = []
            for part in content.split(','):
                part = part.strip()
                if ':' in part:
                    key, value = part.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    # 添加引号
                    pairs.append(f'"{key}": "{value}"')

            fixed = '{' + ', '.join(pairs) + '}'

        return fixed

    def _simple_split(self, cmd: str) -> List[str]:
        """简单分割（shlex 失败时的备用方案）"""
        tokens = []
        current = ""
        in_quote = False
        quote_char = None

        for char in cmd:
            if char in ['"', "'"]:
                if not in_quote:
                    in_quote = True
                    quote_char = char
                elif char == quote_char:
                    in_quote = False
                    quote_char = None
                else:
                    current += char
            elif char == ' ' and not in_quote:
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += char

        if current:
            tokens.append(current)

        return tokens

    def _extract_param_name(self, body: Dict) -> str:
        """从 body 中提取主要参数名"""
        if not body:
            return "query"

        # 优先选择常见参数名
        for param in self.COMMON_PARAMS:
            if param in body:
                return param

        # 返回第一个非系统字段
        for key in body.keys():
            if key.lower() not in self.SKIP_FIELDS:
                return key

        return list(body.keys())[0] if body else "query"

    def _extract_extra_params(self, body: Dict, main_param: str) -> Dict:
        """提取 body 中的其他参数（用于保持原始请求结构）"""
        extra = {}
        for key, value in body.items():
            if key != main_param:
                extra[key] = value
        return extra

    def validate(self, parsed: Dict) -> Dict:
        """验证解析结果并给出建议"""
        validation = {
            "valid": True,
            "warnings": [],
            "suggestions": [],
        }

        if not parsed["url"]:
            validation["valid"] = False
            validation["warnings"].append("URL is required")

        if parsed["method"] == "POST" and not parsed["body"]:
            validation["warnings"].append("POST method but no body data")

        if "Content-Type" not in parsed["headers"] and parsed["body"]:
            validation["suggestions"].append("Consider adding 'Content-Type: application/json' header")

        return validation

    def get_preview(self, curl_cmd: str) -> Dict:
        """
        获取 curl 命令预览（用于前端显示）
        不抛出异常，失败时返回基本信息
        """
        try:
            parsed = self.parse(curl_cmd)
            return {
                "success": True,
                "url": parsed["url"],
                "method": parsed["method"],
                "param_name": parsed["param_name"],
                "has_body": parsed["body"] is not None,
            }
        except Exception as e:
            # 尝试提取 URL
            url_match = re.search(r'https?://[^\s\'"<>]+', curl_cmd)
            return {
                "success": False,
                "url": url_match.group(0) if url_match else "unknown",
                "method": "POST",
                "param_name": "unknown",
                "error": str(e),
            }