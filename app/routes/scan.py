"""
扫描 API 路由
"""

from flask import Blueprint, request, jsonify
from flask_socketio import emit
import asyncio

from ..services.scan_service import ScanService
from scanner.format_detector import APIFormatDetector


scan_bp = Blueprint("scan", __name__)


def get_scan_service():
    """获取扫描服务实例（延迟初始化）"""
    return ScanService()


def get_format_detector():
    """获取格式探测器实例"""
    return APIFormatDetector()


@scan_bp.route("/parse-curl", methods=["POST"])
def parse_curl():
    """
    解析 curl 命令（不执行扫描，只返回解析结果）
    用于前端实时预览

    Request:
        {
            "curl": "curl -X POST https://api.example.com ..."
        }

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "url": "https://api.example.com/chat",
                "method": "POST",
                "param_name": "query",
                "auth_header": "Authorization: Bearer xxx",
                "has_body": true,
                "headers": {...}
            }
        }
    """
    data = request.get_json()
    curl_cmd = data.get("curl", "")

    if not curl_cmd:
        return jsonify({"code": 1, "message": "curl 命令不能为空"}), 400

    if not curl_cmd.strip().lower().startswith("curl "):
        return jsonify({"code": 1, "message": "不是有效的 curl 命令，请以 'curl' 开头"}), 400

    try:
        format_detector = get_format_detector()

        # 同步调用异步方法
        def parse_sync():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(format_detector._detect_from_curl(curl_cmd))
            finally:
                loop.close()

        parsed = parse_sync()

        # 提取认证信息
        auth_header = None
        headers = parsed.get("headers", {})
        for key in ["Authorization", "X-API-Key", "Api-Key", "Bearer", "Token"]:
            if key in headers:
                auth_header = f"{key}: {headers[key][:20]}..." if len(headers[key]) > 20 else f"{key}: {headers[key]}"
                break

        # 如果 Authorization 是 Bearer 格式，显示完整前缀
        if "Authorization" in headers:
            auth_value = headers["Authorization"]
            if auth_value.startswith("Bearer "):
                # 显示 token 前几位
                token_preview = auth_value[7:27] + "..." if len(auth_value) > 27 else auth_value[7:]
                auth_header = f"Bearer {token_preview}"

        return jsonify({
            "code": 0,
            "message": "success",
            "data": {
                "url": parsed.get("url", ""),
                "method": parsed.get("method", "POST"),
                "param_name": parsed.get("param_name", "query"),
                "auth_header": auth_header,
                "has_body": parsed.get("body") is not None,
                "headers": headers,
                "extra_params": parsed.get("extra_params", {})
            }
        })

    except Exception as e:
        return jsonify({"code": 1, "message": f"curl 解析失败: {str(e)}"}), 400


@scan_bp.route("/submit", methods=["POST"])
def submit_scan():
    """
    提交扫描任务

    Request:
        方式1 - curl 命令（推荐）:
        {
            "target_type": "curl",
            "target_value": "curl -X POST http://example.com/api -H 'Authorization: Bearer xxx' -d '{\"query\":\"hello\"}'",
            "param_name": "query"  // 可选，覆盖解析的参数名
        }

        方式2 - URL + 认证:
        {
            "target_type": "url",
            "target_value": "http://example.com/api/query",
            "param_name": "query",
            "auth_token": "Bearer xxx"  // 可选，认证 token
        }

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": "scan_...",
                "status": "queued",
                "estimated_time": 180,
                "format_detected": {"param_name": "query", ...}
            }
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({"code": 1, "message": "请求体不能为空"}), 400

    # 获取输入
    target_value = data.get("target_value") or data.get("url") or data.get("curl") or ""
    target_type = data.get("target_type", "")
    param_name_override = data.get("param_name")  # 用户指定的参数名
    auth_token = data.get("auth_token")  # URL 模式的认证 token
    anonymous_user_id = data.get("anonymous_user_id")

    if not target_value:
        return jsonify({"code": 1, "message": "目标地址必填"}), 400

    # 自动识别输入类型
    if not target_type:
        if target_value.strip().lower().startswith("curl "):
            target_type = "curl"
        else:
            target_type = "url"

    # 处理 curl 命令
    curl_data = None
    format_info = None

    if target_type == "curl" or target_value.strip().lower().startswith("curl "):
        try:
            format_detector = get_format_detector()

            def detect_sync():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(format_detector._detect_from_curl(target_value))
                finally:
                    loop.close()

            curl_data = detect_sync()

            # 如果用户指定了参数名，覆盖解析结果
            if param_name_override:
                curl_data["param_name"] = param_name_override

            format_info = {
                "input_type": "curl",
                "param_name": curl_data.get("param_name"),
                "method": curl_data.get("method"),
                "confidence": 1.0,
            }

            target_type = "url"  # curl 已解析，转为 url 类型

        except Exception as e:
            return jsonify({"code": 1, "message": f"curl 命令解析失败: {str(e)}"}), 400

    else:
        # URL 模式
        format_detector = get_format_detector()
        format_info = {
            "input_type": "url",
            "param_name": param_name_override or "query",
            "method": "POST",
            "confidence": 0.5,
        }

        # 如果有 auth_token，构建 headers
        if auth_token:
            curl_data = {
                "url": target_value,
                "method": "POST",
                "param_name": param_name_override or "query",
                "headers": {"Authorization": auth_token, "Content-Type": "application/json"},
                "extra_params": {}
            }

    # 提交扫描
    scan_service = get_scan_service()
    result = scan_service.submit_scan(
        target_type=target_type,
        target_value=curl_data.get("url", target_value) if curl_data else target_value,
        step=1,
        anonymous_user_id=anonymous_user_id,
        curl_data=curl_data,
        param_name=format_info.get("param_name", "query"),
    )

    # 添加格式探测信息
    if format_info:
        result["data"]["format_detected"] = format_info

    return jsonify(result)


@scan_bp.route("/<task_id>/progress", methods=["GET"])
def get_progress(task_id):
    """
    获取扫描进度

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": "...",
                "status": "running",
                "progress": 50,
                "current_step": "data_leak",
                "score": null
            }
        }
    """
    scan_service = get_scan_service()
    result = scan_service.get_progress(task_id)

    if result["code"] != 0:
        return jsonify(result), 404

    return jsonify(result)


@scan_bp.route("/<task_id>/result", methods=["GET"])
def get_result(task_id):
    """
    获取扫描结果

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": "...",
                "step": 1,
                "is_final": false,
                "score": 85,
                "level": "medium",
                "vulnerabilities": [...],
                "score_breakdown": {...}
            }
        }
    """
    scan_service = get_scan_service()
    result = scan_service.get_result(task_id)

    if result["code"] != 0:
        status_code = 404 if "不存在" in result["message"] else 400
        return jsonify(result), status_code

    return jsonify(result)


@scan_bp.route("/merge", methods=["POST"])
def merge_results():
    """
    合并两次扫描结果

    Request:
        {
            "task_id_step1": "...",
            "task_id_step2": "..."
        }

    Response:
        {
            "code": 0,
            "message": "success",
            "data": {
                "merged_task_id": "...",
                "is_final": true,
                "score": 75,
                "vulnerabilities": [...]
            }
        }
    """
    data = request.get_json()
    task_id_step1 = data.get("task_id_step1")
    task_id_step2 = data.get("task_id_step2")

    if not task_id_step1 or not task_id_step2:
        return jsonify({"code": 1, "message": "task_id_step1 和 task_id_step2 必填"}), 400

    scan_service = get_scan_service()
    result = scan_service.merge_results(task_id_step1, task_id_step2)

    if result["code"] != 0:
        return jsonify(result), 404

    return jsonify(result)