#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 报告生成工具
使用 WeasyPrint 生成专业 PDF 报告
"""

import os
from datetime import datetime
from typing import Any, Dict

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


def generate_pdf_report(result: Dict[str, Any], template: str, reports_dir: str) -> str:
    """
    生成 PDF 报告
    
    Args:
        result: 扫描结果
        template: 模板名称
        reports_dir: 报告目录
    
    Returns:
        PDF 文件路径
    """
    # 生成文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"report_{timestamp}.pdf"
    pdf_path = os.path.join(reports_dir, filename)
    
    # 渲染 HTML
    html_content = render_html_template(result, template)
    
    if WEASYPRINT_AVAILABLE:
        # 使用 WeasyPrint 生成 PDF
        try:
            html = HTML(string=html_content)
            css = CSS(string='''
                @page {
                    size: A4;
                    margin: 2cm;
                    @bottom-right {
                        content: "RAGShield - " counter(page);
                    }
                }
                body { font-family: Arial, sans-serif; }
                .score { font-size: 72px; font-weight: bold; }
                .vuln { page-break-inside: avoid; }
                .watermark {
                    position: fixed;
                    bottom: 50px;
                    right: 50px;
                    opacity: 0.3;
                    font-size: 24px;
                    color: #667eea;
                }
            ''')
            html.write_pdf(pdf_path, stylesheets=[css])
        except Exception as e:
            # 如果 WeasyPrint 失败，回退到 HTML
            html_path = pdf_path.replace('.pdf', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            with open(pdf_path, 'w', encoding='utf-8') as f:
                f.write(f"PDF Report (HTML fallback): {result.get('task_id')}\n")
    else:
        # 回退到 HTML
        html_path = pdf_path.replace('.pdf', '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        with open(pdf_path, 'w', encoding='utf-8') as f:
            f.write(f"PDF Report (HTML fallback): {result.get('task_id')}\n")
    
    return pdf_path


def render_html_template(result: Dict[str, Any], template: str) -> str:
    """渲染 HTML 模板"""
    
    vulnerabilities = result.get('vulnerabilities', [])
    score = result.get('score', 0)
    task_id = result.get('task_id', 'unknown')
    
    # 确定颜色
    if score >= 90:
        color = '#22c55e'
        level = '低风险'
    elif score >= 70:
        color = '#f59e0b'
        level = '中风险'
    else:
        color = '#ef4444'
        level = '高风险'
    
    # 统计
    critical_count = len([v for v in vulnerabilities if v.get('severity') == 'critical'])
    high_count = len([v for v in vulnerabilities if v.get('severity') == 'high'])
    low_count = len([v for v in vulnerabilities if v.get('severity') == 'low'])
    
    html = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>RAG 安全检测报告 - {task_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, "Microsoft YaHei", sans-serif; padding: 40px; color: #333; }}
        h1 {{ color: #667eea; margin-bottom: 10px; font-size: 32px; }}
        h2 {{ color: #333; margin: 30px 0 15px; font-size: 24px; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        h3 {{ color: #555; margin: 20px 0 10px; font-size: 18px; }}
        .subtitle {{ color: #666; margin-bottom: 30px; font-size: 16px; }}
        .score {{ font-size: 72px; color: {color}; font-weight: bold; text-align: center; margin: 30px 0; }}
        .level {{ text-align: center; font-size: 20px; color: #666; margin-bottom: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #667eea; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .vuln {{ border: 1px solid #ddd; padding: 20px; margin: 15px 0; border-radius: 5px; page-break-inside: avoid; }}
        .vuln.critical {{ border-left: 5px solid #ef4444; background: #fef2f2; }}
        .vuln.high {{ border-left: 5px solid #f59e0b; background: #fffbeb; }}
        .vuln.low {{ border-left: 5px solid #22c55e; background: #f0fdf4; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: bold; }}
        .badge.critical {{ background: #ef4444; color: white; }}
        .badge.high {{ background: #f59e0b; color: white; }}
        .badge.low {{ background: #22c55e; color: white; }}
        .watermark {{ position: fixed; bottom: 50px; right: 50px; opacity: 0.3; font-size: 24px; color: #667eea; }}
        .footer {{ margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <h1>🛡️ RAG 安全检测报告</h1>
    <p class="subtitle">任务 ID: {task_id} | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>安全评分</h2>
    <div class="score">{score}/100</div>
    <div class="level">风险等级：{level}</div>
    
    <h2>漏洞统计</h2>
    <table>
        <tr>
            <th>等级</th>
            <th>数量</th>
            <th>扣分</th>
        </tr>
        <tr>
            <td><span class="badge critical">高危</span></td>
            <td>{critical_count}</td>
            <td>{sum([v.get('score_deduction', 0) for v in vulnerabilities if v.get('severity') == 'critical'])}</td>
        </tr>
        <tr>
            <td><span class="badge high">中危</span></td>
            <td>{high_count}</td>
            <td>{sum([v.get('score_deduction', 0) for v in vulnerabilities if v.get('severity') == 'high'])}</td>
        </tr>
        <tr>
            <td><span class="badge low">低危</span></td>
            <td>{low_count}</td>
            <td>{sum([v.get('score_deduction', 0) for v in vulnerabilities if v.get('severity') == 'low'])}</td>
        </tr>
    </table>
    
    <h2>漏洞详情</h2>
'''
    
    for vuln in vulnerabilities:
        severity = vuln.get('severity', 'low')
        severity_cn = '高危' if severity == 'critical' else '中危' if severity == 'high' else '低危'
        html += f'''
    <div class="vuln {severity}">
        <h3>{vuln.get('name', '未知漏洞')}</h3>
        <p><span class="badge {severity}">{severity_cn}</span> | 扣分：{vuln.get('score_deduction', 0)}</p>
        <p style="margin-top: 10px;"><strong>描述：</strong>{vuln.get('description', '')}</p>
        <p style="margin-top: 10px;"><strong>修复建议：</strong>{vuln.get('suggestion', '')}</p>
    </div>
'''
    
    if not vulnerabilities:
        html += '<p style="text-align: center; padding: 50px; font-size: 18px; color: #22c55e;">恭喜！未检测到安全漏洞。</p>'
    
    html += '''
    <div class="footer">
        <p>联系我们获取专业版 RAGuard SDK</p>
        <p>微信：RAGShield | 官网：https://ragshield.com</p>
    </div>
    
    <div class="watermark">
        <p>RAGShield</p>
        <p>专业版</p>
    </div>
</body>
</html>
'''
    
    return html
