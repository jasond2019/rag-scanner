#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF报告生成器
用于Scanner项目的扫描结果报告生成
"""

import os
import uuid
from datetime import datetime
from pathlib import Path


class FallbackReportGenerator:
    """备用报告生成器 - 当WeasyPrint不可用时使用"""
    
    def __init__(self, reports_dir="reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)
    
    def generate(self, scan_result, template="default", watermark=True):
        """生成文本格式的报告"""
        # 生成报告ID
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        txt_path = self.reports_dir / f"{report_id}.txt"

        # 生成文本内容
        content = self._generate_text(scan_result, report_id, template, watermark)

        # 写入文件
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(txt_path)

    def _generate_text(self, scan_result, report_id, template, watermark):
        """生成报告文本内容"""
        task_id = scan_result.get('task_id', 'N/A')
        target_value = scan_result.get('target_value', 'N/A')
        score = scan_result.get('score', 0)
        level = scan_result.get('level', 'unknown')
        vulnerabilities = scan_result.get('vulnerabilities', [])
        
        # 确定风险等级显示
        level_text = {
            'low': '低风险',
            'medium': '中等风险',
            'high': '高风险'
        }.get(level, level)
        
        # 生成报告内容
        content = f"""RAG安全扫描报告
================

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
任务ID: {task_id}
扫描目标: {target_value}
扫描时间: {scan_result.get('created_at', datetime.now().isoformat())}

安全评分: {score}
风险等级: {level_text}

检测到的漏洞:
----------------
"""
        
        if vulnerabilities:
            for i, vuln in enumerate(vulnerabilities, 1):
                content += f"""
{i}. {vuln.get('name', 'Unknown')}
    类型: {vuln.get('type', 'N/A')}
    风险等级: {vuln.get('severity', 'unknown').upper()}
    扣分: -{vuln.get('score_deduction', 0)}
    描述: {vuln.get('description', 'N/A')}
    建议: {vuln.get('suggestion', 'N/A')}
    {'-'*50}
"""
        else:
            content += "\n\\u2728 未发现安全漏洞！\n"
        
        content += f"""
报告ID: {report_id}
机密文档 - 仅供授权人员查阅
"""
        
        return content


class ReportGenerator:
    """扫描报告生成器"""
    
    def __init__(self, reports_dir="reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)
        self._weasyprint_available = self._check_weasyprint()
    
    def _check_weasyprint(self):
        """检查WeasyPrint是否可用"""
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            return True
        except (ImportError, OSError):
            # 使用英文消息避免编码问题
            print("Warning: WeasyPrint cannot be used, will use text report as fallback")
            print("Tip: On Linux/macOS run: pip install WeasyPrint")
            print("Tip: Windows users need to install GTK3 runtime separately")
            return False
    
    def generate(self, scan_result, template="default", watermark=True):
        """生成报告（PDF或文本格式）"""
        if self._weasyprint_available:
            return self._generate_pdf(scan_result, template, watermark)
        else:
            return self._generate_fallback_text(scan_result, template, watermark)
    
    def _generate_pdf(self, scan_result, template="default", watermark=True):
        """生成PDF报告"""
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        
        # 生成报告ID
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        pdf_path = self.reports_dir / f"{report_id}.pdf"
        
        # 生成HTML内容
        html_content = self._generate_html(scan_result, template, watermark)
        
        # 生成PDF
        try:
            font_config = FontConfiguration()
            HTML(string=html_content).write_pdf(
                pdf_path,
                font_config=font_config
            )
            return str(pdf_path)
        except Exception as e:
            print(f"PDF generation failed: {e}")
            # 尝试生成文本报告作为备选
            return self._generate_fallback_text(scan_result, template, watermark)
    
    def _generate_fallback_text(self, scan_result, template, watermark):
        """生成文本格式的报告作为备选方案"""
        fallback_gen = FallbackReportGenerator(str(self.reports_dir))
        return fallback_gen.generate(scan_result, template, watermark)
    
    def _generate_html(self, scan_result, template, watermark):
        """生成报告HTML内容"""
        task_id = scan_result.get('task_id', 'N/A')
        target_value = scan_result.get('target_value', 'N/A')
        score = scan_result.get('score', 0)
        level = scan_result.get('level', 'unknown')
        vulnerabilities = scan_result.get('vulnerabilities', [])

        # 生成报告ID用于显示
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 确定风险等级显示
        level_text = {
            'low': '低风险',
            'medium': '中等风险',
            'high': '高风险'
        }.get(level, level)
        
        level_color = {
            'low': '#28a745',      # 绿色
            'medium': '#ffc107',    # 黄色
            'high': '#dc3545'       # 红色
        }.get(level, '#6c757d')
        
        # 生成漏洞列表
        vuln_items = ""
        if vulnerabilities:
            for i, vuln in enumerate(vulnerabilities, 1):
                severity = vuln.get('severity', 'unknown')
                severity_colors = {
                    'high': '#dc3545',
                    'medium': '#ffc107',
                    'low': '#28a745'
                }
                color = severity_colors.get(severity, '#6c757d')
                
                vuln_items += f"""
                <div class="vulnerability-item">
                    <h4 style="color: {color}; margin: 10px 0;">{i}. {vuln.get('name', 'Unknown')}</h4>
                    <p><strong>类型:</strong> {vuln.get('type', 'N/A')}</p>
                    <p><strong>风险等级:</strong> <span style="color: {color};">{severity.upper()}</span></p>
                    <p><strong>扣分:</strong> -{vuln.get('score_deduction', 0)}</p>
                    <p><strong>描述:</strong> {vuln.get('description', 'N/A')}</p>
                    <p><strong>建议:</strong> {vuln.get('suggestion', 'N/A')}</p>
                </div>
                <hr style="margin: 15px 0; border: 0; border-top: 1px solid #eee;" />
                """
        else:
            vuln_items = "<p>\\u2728 未发现安全漏洞！</p>"
        
        # 添加水印（如果需要）
        watermark_html = ""
        if watermark:
            watermark_html = """
            <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-45deg); 
                        opacity: 0.05; font-size: 80px; color: black; z-index: -1; pointer-events: none;
                        white-space: nowrap;">
                SCANNER REPORT
            </div>
            """
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>RAG安全扫描报告 - {task_id}</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 40px; 
                    line-height: 1.6; 
                    background-color: white;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #007bff;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .summary-box {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 30px;
                }}
                .score-display {{
                    font-size: 3em;
                    font-weight: bold;
                    text-align: center;
                    margin: 20px 0;
                }}
                .level-display {{
                    text-align: center;
                    font-size: 1.5em;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 5px;
                    color: white;
                    background-color: {level_color};
                }}
                .vulnerability-item {{
                    margin: 20px 0;
                    padding: 15px;
                    border-left: 4px solid {level_color};
                    background-color: #f8f9fa;
                }}
                .watermark {{
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%) rotate(-45deg);
                    opacity: 0.05;
                    font-size: 80px;
                    color: black;
                    z-index: -1;
                    pointer-events: none;
                    white-space: nowrap;
                }}
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    color: #6c757d;
                    font-size: 0.9em;
                    border-top: 1px solid #eee;
                    padding-top: 20px;
                }}
            </style>
        </head>
        <body>
            {watermark_html}
            <div class="header">
                <h1>🔍 RAG安全扫描报告</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary-box">
                <h2>扫描摘要</h2>
                <p><strong>任务ID:</strong> {task_id}</p>
                <p><strong>扫描目标:</strong> {target_value}</p>
                <p><strong>扫描时间:</strong> {scan_result.get('created_at', datetime.now().isoformat())}</p>
            </div>
            
            <div class="score-display" style="color: {level_color};">
                {score}
            </div>
            
            <div class="level-display">
                {level_text}
            </div>
            
            <h3>检测到的漏洞</h3>
            {vuln_items}
            
            <div class="footer">
                <p>RAG Security Scanner 报告 | 机密文档 | 仅供授权人员查阅</p>
                <p>报告ID: {report_id}</p>
            </div>
        </body>
        </html>
        """
        
        return html_template


# 测试报告生成
if __name__ == "__main__":
    generator = ReportGenerator()
    
    # 模拟扫描结果
    sample_result = {
        "task_id": "test_task_12345",
        "target_value": "http://localhost:5001",
        "score": 70,
        "level": "medium",
        "vulnerabilities": [
            {
                "name": "提示词注入",
                "type": "prompt_injection",
                "severity": "high",
                "score_deduction": 15,
                "description": "系统易受提示词注入攻击，可能导致系统指令泄露",
                "suggestion": "实施输入过滤和输出审查机制"
            },
            {
                "name": "数据泄露",
                "type": "data_leak",
                "severity": "medium",
                "score_deduction": 10,
                "description": "查询结果返回过多敏感信息",
                "suggestion": "实施数据脱敏和访问控制"
            }
        ],
        "created_at": datetime.now().isoformat()
    }
    
    try:
        report_path = generator.generate(sample_result, watermark=True)
        print(f"\\u2714\\uFE0F Report generated successfully: {report_path}")
    except Exception as e:
        print(f"\\u274C Report generation failed: {e}")