/**
 * PDF Report Generator
 * 使用 pdfmake 在浏览器端生成安全报告 PDF
 */

// 风险等级颜色映射
const LEVEL_COLORS = {
    critical: '#c53030',
    high: '#dd6b20',
    medium: '#d69e2e',
    low: '#38a169'
};

// 评分颜色
function getScoreColor(score) {
    if (score >= 90) return '#38a169';
    if (score >= 70) return '#d69e2e';
    return '#e53e3e';
}

// 生成 pdfmake 文档定义
function generatePDFDefinition(reportData) {
    const { task, summary, vulnerabilities, recommendations, scan_dimensions, scan_config, report_id, generated_at } = reportData;

    const scoreColor = getScoreColor(task.score || 0);
    const levelColor = LEVEL_COLORS[task.level] || '#666';

    // 扫描维度表格
    const dimensionTableBody = [
        [
            { text: 'Dimension', style: 'tableHeader' },
            { text: 'Rules', style: 'tableHeader' },
            { text: 'Result', style: 'tableHeader' },
            { text: 'Vulns', style: 'tableHeader' },
            { text: 'Impact', style: 'tableHeader' }
        ]
    ];

    if (scan_dimensions && scan_dimensions.length > 0) {
        scan_dimensions.forEach(dim => {
            const passed = dim.vulnerabilities_found === 0;
            dimensionTableBody.push([
                { text: dim.name.substring(0, 25), fontSize: 9 },
                dim.rules_count.toString(),
                { text: passed ? 'PASSED' : 'FAILED',
                  color: passed ? '#38a169' : '#e53e3e',
                  bold: true,
                  alignment: 'center' },
                dim.vulnerabilities_found.toString(),
                `-${dim.score_impact || 0} pts`
            ]);
        });
    }

    // 漏洞表格数据
    const vulnTableBody = [
        [
            { text: 'Severity', style: 'tableHeader' },
            { text: 'Rule ID', style: 'tableHeader' },
            { text: 'Name', style: 'tableHeader' },
            { text: 'Impact', style: 'tableHeader' },
            { text: 'Description', style: 'tableHeader' }
        ]
    ];

    if (vulnerabilities && vulnerabilities.length > 0) {
        vulnerabilities.forEach(v => {
            vulnTableBody.push([
                { text: v.severity.toUpperCase(),
                  style: `severity_${v.severity}`,
                  alignment: 'center' },
                v.rule_id || 'N/A',
                v.name,
                `-${v.score_deduction || 0}`,
                (v.description || '').substring(0, 60) + ((v.description || '').length > 60 ? '...' : '')
            ]);
        });
    } else {
        vulnTableBody.push([
            { text: 'No vulnerabilities found', colSpan: 5, alignment: 'center', color: '#38a169' },
            '', '', '', ''
        ]);
    }

    // 目标信息表格
    const targetTableBody = [
        ['Target URL', task.target_value || 'N/A'],
        ['Target Type', (task.target_type || 'unknown').toUpperCase()],
        ['Scan Status', (task.status || 'unknown').toUpperCase()],
        ['Scan Date', task.created_at || generated_at]
    ];

    // 漏洞摘要表格
    const summaryTableBody = [
        [
            { text: 'Severity', style: 'tableHeader' },
            { text: 'Count', style: 'tableHeader' },
            { text: 'Score Impact', style: 'tableHeader' }
        ],
        [
            { text: 'Critical', color: LEVEL_COLORS.critical, bold: true },
            (summary.critical_count || 0).toString(),
            `-${(summary.critical_count || 0) * 15} pts`
        ],
        [
            { text: 'High', color: LEVEL_COLORS.high, bold: true },
            (summary.high_count || 0).toString(),
            `-${(summary.high_count || 0) * 10} pts`
        ],
        [
            { text: 'Medium', color: LEVEL_COLORS.medium, bold: true },
            (summary.medium_count || 0).toString(),
            `-${(summary.medium_count || 0) * 5} pts`
        ],
        [
            { text: 'Low', color: LEVEL_COLORS.low, bold: true },
            (summary.low_count || 0).toString(),
            `-${(summary.low_count || 0) * 2} pts`
        ]
    ];

    // 建议列表
    const recommendationList = [];
    if (recommendations && recommendations.length > 0) {
        recommendations.forEach((r, idx) => {
            recommendationList.push({
                text: [
                    { text: `${idx + 1}. [${(r.priority || 'medium').toUpperCase()}] `, bold: true },
                    { text: r.description || '' },
                    { text: '\n   Recommended actions: ', italics: true },
                    { text: (r.actions || []).join(', ') }
                ],
                margin: [0, 5, 0, 10]
            });
        });
    } else {
        recommendationList.push({
            text: 'No specific recommendations available.',
            color: '#666'
        });
    }

    // 文档定义
    return {
        pageSize: 'A4',
        pageMargins: [40, 60, 40, 60],

        // 页眉
        header: {
            columns: [
                { text: 'RAG Scanner', style: 'headerLeft', width: '40%' },
                { text: 'Security Assessment Report', style: 'headerRight', width: '60%', alignment: 'right' }
            ],
            margin: [40, 20, 40, 10]
        },

        // 页脚
        footer: function(currentPage, pageCount) {
            return {
                columns: [
                    { text: `Page ${currentPage} of ${pageCount}`, alignment: 'left', fontSize: 9, color: '#666' },
                    { text: 'Generated by RAG Scanner', alignment: 'right', fontSize: 9, color: '#666' }
                ],
                margin: [40, 20, 40, 0]
            };
        },

        // 内容
        content: [
            // 报告元信息
            {
                columns: [
                    { text: `Report ID: ${report_id}`, style: 'metaInfo', width: '50%' },
                    { text: `Generated: ${generated_at}`, style: 'metaInfo', width: '50%', alignment: 'right' }
                ],
                margin: [0, 0, 0, 15]
            },

            // 分隔线
            {
                canvas: [
                    { type: 'line', x1: 0, y1: 0, x2: 515, y2: 0, lineWidth: 1, lineColor: '#e0e0e0' }
                ],
                margin: [0, 5, 0, 15]
            },

            // 目标信息
            { text: 'TARGET INFORMATION', style: 'sectionTitle' },
            {
                table: {
                    widths: ['30%', '70%'],
                    body: targetTableBody
                },
                layout: {
                    hLineWidth: function(i) { return i === 0 ? 1 : 0.5; },
                    vLineWidth: function() { return 0; },
                    hLineColor: function() { return '#e0e0e0'; },
                    paddingLeft: function() { return 8; },
                    paddingRight: function() { return 8; },
                    paddingTop: function() { return 6; },
                    paddingBottom: function() { return 6; }
                },
                margin: [0, 5, 0, 20]
            },

            // 安全评分
            { text: 'SECURITY SCORE', style: 'sectionTitle' },
            {
                columns: [
                    {
                        width: '55%',
                        stack: [
                            {
                                table: {
                                    widths: ['*'],
                                    body: [
                                        [{
                                            text: `${task.score || 0}`,
                                            style: 'scoreNumber',
                                            fillColor: scoreColor,
                                            alignment: 'center'
                                        }]
                                    ]
                                },
                                layout: 'noBorders'
                            },
                            {
                                text: 'out of 100',
                                alignment: 'center',
                                fontSize: 12,
                                color: '#666',
                                margin: [0, 5, 0, 0]
                            }
                        ]
                    },
                    {
                        width: '45%',
                        stack: [
                            {
                                table: {
                                    widths: ['*'],
                                    body: [
                                        [{
                                            text: `RISK LEVEL: ${(task.level || 'unknown').toUpperCase()}`,
                                            style: 'levelBadge',
                                            fillColor: levelColor,
                                            alignment: 'center'
                                        }]
                                    ]
                                },
                                layout: 'noBorders'
                            }
                        ]
                    }
                ],
                margin: [0, 5, 0, 20]
            },

            // 扫描维度
            { text: 'SCAN DIMENSIONS', style: 'sectionTitle' },
            {
                text: `Total: ${scan_config?.dimensions || 6} dimensions, ${scan_config?.total_rules || 963} rules`,
                style: 'metaInfo',
                margin: [0, 0, 0, 10]
            },
            {
                table: {
                    widths: ['35%', '15%', '20%', '15%', '15%'],
                    body: dimensionTableBody
                },
                layout: {
                    hLineWidth: function(i) { return i === 0 ? 1 : 0.5; },
                    vLineWidth: function() { return 0; },
                    hLineColor: function() { return '#e0e0e0'; },
                    paddingLeft: function() { return 6; },
                    paddingRight: function() { return 6; },
                    paddingTop: function() { return 5; },
                    paddingBottom: function() { return 5; },
                    fillColor: function(i) { return i === 0 ? '#f8f9fa' : null; }
                },
                margin: [0, 5, 0, 20]
            },

            // 漏洞摘要
            { text: 'VULNERABILITY SUMMARY', style: 'sectionTitle' },
            {
                table: {
                    widths: ['35%', '25%', '40%'],
                    body: summaryTableBody
                },
                layout: {
                    hLineWidth: function(i) { return i === 0 ? 1 : 0.5; },
                    vLineWidth: function() { return 0; },
                    hLineColor: function() { return '#e0e0e0'; },
                    paddingLeft: function() { return 8; },
                    paddingRight: function() { return 8; },
                    paddingTop: function() { return 6; },
                    paddingBottom: function() { return 6; },
                    fillColor: function(i) { return i === 0 ? '#f8f9fa' : null; }
                },
                margin: [0, 5, 0, 20]
            },

            // 漏洞详情表格
            { text: 'DETAILED VULNERABILITIES', style: 'sectionTitle' },
            {
                table: {
                    widths: ['12%', '12%', '28%', '10%', '38%'],
                    body: vulnTableBody,
                    dontBreakRows: true
                },
                layout: {
                    hLineWidth: function(i) { return i === 0 ? 1 : 0.5; },
                    vLineWidth: function() { return 0; },
                    hLineColor: function() { return '#e0e0e0'; },
                    paddingLeft: function() { return 6; },
                    paddingRight: function() { return 6; },
                    paddingTop: function() { return 5; },
                    paddingBottom: function() { return 5; },
                    fillColor: function(i) { return i === 0 ? '#f8f9fa' : null; }
                },
                margin: [0, 5, 0, 20]
            },

            // 建议
            { text: 'RECOMMENDATIONS', style: 'sectionTitle' },
            {
                stack: recommendationList,
                margin: [0, 5, 0, 20]
            },

            // 免责声明
            { text: 'DISCLAIMER', style: 'sectionTitle' },
            {
                text: 'This report is generated automatically by RAG Scanner. Results are based on automated security tests and may not reflect all possible vulnerabilities. Manual verification is recommended for critical systems.',
                style: 'disclaimer'
            }
        ],

        // 样式定义
        styles: {
            headerLeft: { fontSize: 18, bold: true, color: '#667eea' },
            headerRight: { fontSize: 14, color: '#666' },
            metaInfo: { fontSize: 10, color: '#888' },
            sectionTitle: { fontSize: 13, bold: true, color: '#333', margin: [0, 10, 0, 5] },
            tableHeader: { fontSize: 10, bold: true, color: '#333' },
            scoreNumber: { fontSize: 36, bold: true, color: '#ffffff' },
            levelBadge: { fontSize: 14, bold: true, color: '#ffffff' },
            severity_critical: { fontSize: 9, bold: true, color: '#c53030' },
            severity_high: { fontSize: 9, bold: true, color: '#dd6b20' },
            severity_medium: { fontSize: 9, bold: true, color: '#d69e2e' },
            severity_low: { fontSize: 9, bold: true, color: '#38a169' },
            disclaimer: { fontSize: 9, color: '#999', italics: true, margin: [0, 5, 0, 0] }
        },

        // 默认样式
        defaultStyle: {
            fontSize: 10,
            color: '#333'
        }
    };
}

// 生成并下载 PDF 报告
async function downloadPDFReport(taskId) {
    // 显示加载提示
    const downloadBtn = document.getElementById('downloadBtn');
    const originalText = downloadBtn.textContent;
    downloadBtn.textContent = 'Generating PDF...';
    downloadBtn.disabled = true;

    try {
        // 1. 从 API 获取报告数据
        const response = await fetch(`${API_URL}/api/report/generate?task_id=${taskId}`);
        const result = await response.json();

        if (result.code !== 0) {
            throw new Error(result.message || 'Failed to fetch report data');
        }

        const reportData = result.data;

        // 2. 生成 PDF 定义
        const docDefinition = generatePDFDefinition(reportData);

        // 3. 创建并下载 PDF
        pdfMake.createPdf(docDefinition).download(`security-report-${taskId}.pdf`);

        console.log('PDF report downloaded successfully');

        // 恢复按钮状态
        downloadBtn.textContent = originalText;
        downloadBtn.disabled = false;

    } catch (error) {
        console.error('PDF generation failed:', error);

        // 恢复按钮状态
        downloadBtn.textContent = originalText;
        downloadBtn.disabled = false;

        // 显示错误提示
        alert('PDF generation failed: ' + error.message + '\n\nFalling back to JSON download...');

        // 失败时 fallback 到 JSON 下载
        window.open(`${API_URL}/api/report/download?task_id=${taskId}`, '_blank');
    }
}

// 导出全局函数
window.downloadPDFReport = downloadPDFReport;