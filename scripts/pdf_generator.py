#!/usr/bin/env python3
"""
PDF Report Generator for Stock Analysis
生成专业股票分析报告 PDF
"""

import os
import markdown
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class ReportGenerator:
    """股票分析报告 PDF 生成器"""

    def __init__(self):
        self.output_dir = Path(__file__).parent / "reports"
        self.output_dir.mkdir(exist_ok=True)

    @staticmethod
    def _render_markdown(text: str) -> str:
        """把 Markdown 转为 HTML"""
        if not text:
            return ""
        return markdown.markdown(text, extensions=['nl2br', 'tables'])

    def generate(
        self,
        analysis_result: Dict[str, Any],
        output_dir: Optional[str] = None,
        template: str = "professional"
    ) -> str:
        """
        生成 PDF 报告

        Args:
            analysis_result: StockAnalyst.analyze() 返回的结果
            output_dir: 输出目录（可选）
            template: 模板名称

        Returns:
            PDF 文件路径
        """
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = self.output_dir

        output_path.mkdir(parents=True, exist_ok=True)

        stock_code = analysis_result["stock_code"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{stock_code}_{timestamp}.pdf"
        pdf_path = output_path / filename

        # 数据预处理：自动修复常见问题
        analysis_result = self._preprocess_data(analysis_result)

        html_content = self._generate_html(analysis_result)
        self._html_to_pdf(html_content, pdf_path)

        return str(pdf_path)

    def _preprocess_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """预处理分析结果数据，自动修复常见问题"""
        import copy
        result = copy.deepcopy(result)

        # 1. 修复新闻摘要
        news_analyst = result.get("parallel_analysis", {}).get("news_analyst", {})
        news_list = news_analyst.get("news_list", [])
        for news in news_list:
            summary = (news.get("summary") or "").strip()
            if not summary:
                # fallback 1: snippet
                summary = (news.get("snippet") or "").strip()
            if not summary:
                # fallback 2: title
                title = news.get("title", "")
                summary = title  # 直接用 title
            news["summary"] = summary if summary.strip() else "暂无摘要"

        # 2. 修复交易价格：如果 Agent 传入了字符串类型的价格描述而非数字
        trading = result.get("trading_plan", {})
        price_fields = ["buy_price", "target_price", "stop_loss"]
        for field in price_fields:
            val = trading.get(field)
            if val is not None and not isinstance(val, (int, float)):
                try:
                    trading[field] = float(val)
                except (ValueError, TypeError):
                    # 非数字字符串如 "现行价格" -> 设为 None，让模板显示 fallback
                    trading[field] = None

        # 3. 计算参考价格（如果缺少决策价格但有当前价格）
        current_price = result.get("current_price")
        if current_price and trading:
            # 如果没有决策价格但有当前价格，计算参考价格
            if trading.get("buy_price") is None:
                trading["reference_price"] = current_price
                trading["reference_target"] = round(current_price * 1.10, 2)
                trading["reference_stop"] = round(current_price * 0.95, 2)

        # 4. 诚实空缺检测（优先使用明确的失败标记）
        trading = result.get("trading_plan", {})

        # 检测 position_size 是否为空缺
        # 注意: '0%' 是合法的观望建议，不是数据获取失败
        if "_position_size_failed" in trading:
            pass
        elif trading.get("position_size") in [None, ""]:
            trading["_position_size_failed"] = True
        else:
            trading["_position_size_failed"] = False

        # 检测 exit_criteria 是否为空缺
        # 注意: '不适用'/'等待更好时机' 是合法的观望回答，不是数据获取失败
        if "_exit_criteria_failed" in trading:
            pass
        elif trading.get("exit_criteria") in [None, ""]:
            trading["_exit_criteria_failed"] = True
        else:
            trading["_exit_criteria_failed"] = False

        return result

    @staticmethod
    def _format_price(price, fallback: str = "N/A", reference: float = None) -> str:
        """格式化价格显示，兼容数字和字符串类型"""
        if price is None and reference is not None:
            return f"参考 ¥{reference:.2f}"
        if price is None:
            return fallback
        if isinstance(price, (int, float)):
            return f"¥{price:.2f}"
        # 字符串类型：尝试转为数字
        try:
            return f"¥{float(price):.2f}"
        except (ValueError, TypeError):
            # 非数字字符串（如 "现行价格"）直接返回
            return str(price) if str(price).strip() else fallback

    def _generate_html(self, result: Dict[str, Any]) -> str:
        """生成 HTML 格式的报告"""
        stock_code = result["stock_code"]
        timestamp = result["timestamp"]
        final = result["final_decision"]
        trading = result["trading_plan"]
        manager = result["manager_decision"]
        risk = result["risk_debate"]
        parallel = result["parallel_analysis"]
        news_analyst = parallel["news_analyst"]
        social_analyst = parallel["social_analyst"]

        # 生成新闻列表 HTML
        news_list_html = ""
        if news_analyst.get("news_list") and len(news_analyst["news_list"]) > 0:
            for news in news_analyst["news_list"]:
                sentiment_color = "#2e7d32" if "多" in news.get("sentiment", "") or "正" in news.get("sentiment", "") else ("#c62828" if "空" in news.get("sentiment", "") or "负" in news.get("sentiment", "") else "#666")
                # 摘要 fallback：summary > snippet > title
                summary_text = (news.get('summary') or '').strip()
                if not summary_text:
                    summary_text = (news.get('snippet') or '').strip()
                if not summary_text:
                    summary_text = news.get('title', '暂无摘要')
                news_list_html += f"""
                <div class="news-item">
                    <div class="news-header">
                        <span class="news-title">{news.get('title', '')}</span>
                        <span class="news-sentiment" style="color:{sentiment_color}">{news.get('sentiment', '')}</span>
                    </div>
                    <div class="news-meta">
                        <span class="news-date">{news.get('date', '')}</span>
                        <span class="news-source">{news.get('source', '')}</span>
                    </div>
                    <div class="news-summary">{summary_text}</div>
                    {f'<div class="news-url"><a href="{news.get("url", "")}" target="_blank">原文链接</a></div>' if news.get("url") else ""}
                </div>
                """
        else:
            news_list_html = '<div class="no-news">暂无新闻数据，请使用 web_search MCP tool 获取近期新闻</div>'

        # 生成社交媒体 HTML
        social_html = ""
        if social_analyst.get("platforms"):
            for platform in social_analyst["platforms"]:
                social_html += f"<li>{platform.get('name', '')}: {platform.get('sentiment', '')} (热度: {platform.get('heat', '')})</li>"
        else:
            social_html = f"""
            <li>雪球讨论热度: {social_analyst.get('platforms', [{}])[0].get('heat', '暂无数据') if social_analyst.get('platforms') else '暂无数据'}</li>
            <li>东方财富股吧情绪: {social_analyst.get('sentiment_score', '暂无数据')}</li>
            <li>机构评级汇总: 暂无机构评级数据，需对接券商数据源</li>
            """

        # 生成技术分析 HTML
        tech_analyst_data = parallel.get("tech_analyst", {})
        ta = tech_analyst_data.get("technical_analysis", {})
        trend = ta.get("趋势判断", {})
        indicators = ta.get("关键指标", {})
        advice = ta.get("操作建议", {})
        tech_summary = ta.get("技术信号总结", "") or (tech_analyst_data.get("analysis", [""])[0] if tech_analyst_data.get("analysis") else "待分析")

        tech_html = "<ul>"
        if trend and isinstance(trend, dict) and trend:
            tech_html += "<li><strong>趋势判断：</strong> "
            tech_html += " / ".join(f"{k}: {v}" for k, v in trend.items() if v)
            tech_html += "</li>"
        if indicators and isinstance(indicators, dict) and indicators:
            tech_html += "<li><strong>关键指标：</strong></li>"
            for k, v in indicators.items():
                tech_html += f'<li style="margin-left:16px">{k}: {v}</li>'
        if advice and isinstance(advice, dict) and advice:
            tech_html += "<li><strong>操作建议：</strong></li>"
            for k, v in advice.items():
                tech_html += f'<li style="margin-left:16px">{k}: {v}</li>'
        if tech_summary:
            tech_html += f"<li><strong>技术信号：</strong>{tech_summary}</li>"
        if not trend and not indicators and not advice:
            tech_html = "<ul><li>待分析</li>"
        tech_html += "</ul>"

        # 生成基本面分析 HTML
        fund_analyst_data = parallel.get("fundamentals_analyst", {})
        fa = fund_analyst_data.get("fundamentals_analysis", {})
        valuation = fa.get("估值分析", {})
        profitability = fa.get("盈利能力", {})
        growth = fa.get("成长性", {})
        health = fa.get("财务健康", {})
        fund_summary = fa.get("综合评价", "") or (fund_analyst_data.get("analysis", [""])[0] if fund_analyst_data.get("analysis") else "待分析")

        fund_html = "<ul>"
        if valuation and isinstance(valuation, dict) and valuation:
            fund_html += "<li><strong>估值分析：</strong></li>"
            for k, v in valuation.items():
                if isinstance(v, dict):
                    fund_html += f'<li style="margin-left:16px">{k}: {v.get("数值", "待计算")} (行业: {v.get("行业平均", "待计算")}, {v.get("评价", "")})</li>'
                else:
                    fund_html += f'<li style="margin-left:16px">{k}: {v}</li>'
        if profitability and isinstance(profitability, dict) and profitability:
            fund_html += "<li><strong>盈利能力：</strong></li>"
            for k, v in profitability.items():
                if isinstance(v, dict):
                    fund_html += f'<li style="margin-left:16px">{k}: {v.get("数值", "待计算")} (同比: {v.get("同比变化", "")})</li>'
                else:
                    fund_html += f'<li style="margin-left:16px">{k}: {v}</li>'
        if growth and isinstance(growth, dict) and growth:
            fund_html += "<li><strong>成长性：</strong></li>"
            for k, v in growth.items():
                fund_html += f'<li style="margin-left:16px">{k}: {v}</li>'
        if health and isinstance(health, dict) and health:
            fund_html += "<li><strong>财务健康：</strong></li>"
            for k, v in health.items():
                fund_html += f'<li style="margin-left:16px">{k}: {v}</li>'
        if fund_summary:
            fund_html += f"<li><strong>综合评价：</strong>{fund_summary}</li>"
        if not valuation and not profitability and not growth and not health:
            fund_html = "<ul><li>待分析</li>"
        fund_html += "</ul>"

        # 生成辩论 HTML
        debate_html = ""
        debate_rounds = result.get("debate", {}).get("rounds", [])
        if debate_rounds:
            for i, r in enumerate(debate_rounds):
                round_num = r.get("round", i + 1)
                
                # 检查是否有详细的多头论证结构
                bull_detail = r.get("bull_detail", {})
                bear_detail = r.get("bear_detail", {})
                
                # 生成多头论证 HTML
                if bull_detail and isinstance(bull_detail, dict):
                    bull_items_html = ""
                    for dim_name, dim_data in bull_detail.items():
                        if isinstance(dim_data, dict):
                            point = dim_data.get("论点", dim_data.get("point", ""))
                            data = dim_data.get("支撑数据", dim_data.get("data", ""))
                            conclusion = dim_data.get("结论", dim_data.get("conclusion", ""))
                            if point:
                                bull_items_html += f'''
                                <div class="debate-argument">
                                    <div class="debate-argument-title">◆ {dim_name}</div>
                                    <div class="debate-argument-content">
                                        <div><strong>论点：</strong>{point}</div>'''
                                if data:
                                    bull_items_html += f'''
                                        <div><strong>支撑：</strong>{data}</div>'''
                                if conclusion:
                                    bull_items_html += f'''
                                        <div class="debate-conclusion">{conclusion}</div>'''
                                bull_items_html += "</div></div>"
                        elif isinstance(dim_data, str):
                            bull_items_html += f'''
                                <div class="debate-argument">
                                    <div class="debate-argument-title">◆ {dim_name}</div>
                                    <div class="debate-argument-content">{dim_data}</div>
                                </div>'''
                elif r.get("bull_points"):
                    bull_pts_list = r.get("bull_points", [])
                    if isinstance(bull_pts_list, list) and len(bull_pts_list) > 0:
                        bull_items_html = "<ul>" + "".join(f"<li>{pt}</li>" for pt in bull_pts_list[:5]) + "</ul>"
                    else:
                        bull_items_html = f"<p>{bull_pts_list}</p>" if bull_pts_list else "<p>待补充</p>"
                else:
                    bull_items_html = "<p>待补充</p>"
                
                # 生成空头论证 HTML
                if bear_detail and isinstance(bear_detail, dict):
                    bear_items_html = ""
                    for dim_name, dim_data in bear_detail.items():
                        if isinstance(dim_data, dict):
                            point = dim_data.get("论点", dim_data.get("point", ""))
                            data = dim_data.get("支撑数据", dim_data.get("data", ""))
                            conclusion = dim_data.get("结论", dim_data.get("conclusion", ""))
                            if point:
                                bear_items_html += f'''
                                <div class="debate-argument bear">
                                    <div class="debate-argument-title">◆ {dim_name}</div>
                                    <div class="debate-argument-content">
                                        <div><strong>论点：</strong>{point}</div>'''
                                if data:
                                    bear_items_html += f'''
                                        <div><strong>支撑：</strong>{data}</div>'''
                                if conclusion:
                                    bear_items_html += f'''
                                        <div class="debate-conclusion">{conclusion}</div>'''
                                bear_items_html += "</div></div>"
                        elif isinstance(dim_data, str):
                            bear_items_html += f'''
                                <div class="debate-argument bear">
                                    <div class="debate-argument-title">◆ {dim_name}</div>
                                    <div class="debate-argument-content">{dim_data}</div>
                                </div>'''
                elif r.get("bear_points"):
                    bear_pts_list = r.get("bear_points", [])
                    if isinstance(bear_pts_list, list) and len(bear_pts_list) > 0:
                        bear_items_html = "<ul>" + "".join(f"<li>{pt}</li>" for pt in bear_pts_list[:5]) + "</ul>"
                    else:
                        bear_items_html = f"<p>{bear_pts_list}</p>" if bear_pts_list else "<p>待补充</p>"
                else:
                    bear_items_html = "<p>待补充</p>"
                
                # 组合辩论卡片
                debate_html += f'''
                <div class="debate-round">
                    <h4 class="debate-round-title">第{round_num}轮辩论</h4>
                    <div class="debate-columns">
                        <div class="debate-column bull">
                            <div class="debate-column-header">多方论点</div>
                            {bull_items_html}
                        </div>
                        <div class="debate-column bear">
                            <div class="debate-column-header">空方论点</div>
                            {bear_items_html}
                        </div>
                    </div>
                </div>'''
        else:
            debate_html = "<p class=\"no-data\">辩论数据待生成</p>"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票分析报告 - {stock_code}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: "PingFang SC", "Microsoft YaHei", "SimHei", sans-serif; line-height: 1.6; color: #333; font-size: 12px; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 30px; }}
        .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #1a73e8; padding-bottom: 15px; }}
        .header h1 {{ color: #1a73e8; font-size: 24px; margin-bottom: 8px; }}
        .header .meta {{ color: #666; font-size: 11px; }}
        .section {{ margin-bottom: 25px; }}
        .section h2 {{ color: #1a73e8; font-size: 16px; border-left: 4px solid #1a73e8; padding-left: 10px; margin-bottom: 12px; }}
        .decision-box {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 15px; text-align: center; }}
        .decision-box .big {{ font-size: 28px; font-weight: bold; color: #1a73e8; }}
        .decision-box .sub {{ color: #666; margin-top: 8px; font-size: 11px; }}
        .target-prices {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 15px 0; }}
        .price-card {{ background: #f5f5f5; padding: 12px; border-radius: 8px; text-align: center; }}
        .price-card .label {{ color: #666; font-size: 10px; }}
        .price-card .value {{ font-size: 18px; font-weight: bold; color: #1a73e8; }}
        .analyst-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .analyst-card {{ background: #f9f9f9; padding: 12px; border-radius: 8px; border-left: 3px solid #1a73e8; }}
        .analyst-card h4 {{ color: #1a73e8; margin-bottom: 6px; font-size: 12px; }}
        .analyst-card ul {{ padding-left: 18px; font-size: 11px; }}
        .risk-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
        .risk-table th, .risk-table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        .risk-table th {{ background: #f5f5f5; }}
        .disclaimer {{ background: #fff3cd; padding: 12px; border-radius: 8px; font-size: 10px; color: #856404; margin-top: 20px; }}
        .footer {{ text-align: center; margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; color: #999; font-size: 10px; }}

        /* 新闻样式 */
        .news-section {{ background: #fafafa; padding: 15px; border-radius: 8px; }}
        .news-item {{ background: #fff; padding: 12px; margin-bottom: 10px; border-radius: 6px; border: 1px solid #eee; }}
        .news-item:last-child {{ margin-bottom: 0; }}
        .news-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
        .news-title {{ font-weight: bold; color: #333; font-size: 12px; flex: 1; }}
        .news-sentiment {{ font-size: 10px; padding: 2px 8px; border-radius: 10px; background: #f0f0f0; }}
        .news-meta {{ font-size: 10px; color: #888; margin-bottom: 6px; }}
        .news-date {{ margin-right: 15px; }}
        .news-summary {{ font-size: 11px; color: #555; line-height: 1.5; }}
        .news-url {{ margin-top: 6px; font-size: 10px; }}
        .news-url a {{ color: #1a73e8; text-decoration: none; }}
        .no-news {{ text-align: center; color: #999; padding: 20px; font-size: 12px; }}

        .sentiment-summary {{ background: #e8f5e9; padding: 10px; border-radius: 6px; margin-bottom: 15px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>股票分析报告</h1>
            <div class="meta">
                <div>股票代码: {stock_code}</div>
                <div>报告生成时间: {timestamp}</div>
                <div>分析框架: TradingAgents-CN 多智能体</div>
            </div>
        </div>

        <!-- 执行摘要 -->
        <div class="section">
            <h2>执行摘要</h2>
            <div class="decision-box">
                <div class="big">{final["final_recommendation"]}</div>
                <div class="sub">风险等级: {final["risk_level"]} | 投资期限: {final["investment_horizon"]}</div>
            </div>
            <p><strong>核心逻辑:</strong> {manager["rationale"]}</p>
        </div>

        <!-- 目标价位 -->
        <div class="section">
            <h2>交易计划</h2>
            <div class="target-prices">
                <div class="price-card">
                    <div class="label">买入价格</div>
                    <div class="value">{self._format_price(trading.get("buy_price"), "观望", trading.get("reference_price"))}</div>
                </div>
                <div class="price-card">
                    <div class="label">目标价格</div>
                    <div class="value">{self._format_price(trading.get("target_price"), "待定", trading.get("reference_target"))}</div>
                </div>
                <div class="price-card">
                    <div class="label">止损价格</div>
                    <div class="value">{self._format_price(trading.get("stop_loss"), "不适用", trading.get("reference_stop"))}</div>
                </div>
            </div>
            <p><strong>仓位建议:</strong> {'<span style="color:#c62828">数据获取失败</span>' if trading.get('_position_size_failed') else trading.get('position_size', '')}
</p>
            <p><strong>入场条件:</strong> {trading.get("entry_criteria", "")}</p>
            <p><strong>出场条件:</strong> {'<span style="color:#c62828">数据获取失败</span>' if trading.get('_exit_criteria_failed') else trading.get('exit_criteria', '')}
</p>
        </div>

        <!-- 新闻与情绪分析 -->
        <div class="section">
            <h2>新闻与情绪分析</h2>
            <div class="news-section">
                <div class="sentiment-summary">
                    <strong>新闻情绪:</strong> {news_analyst.get("sentiment", "待获取")} | 共 {news_analyst.get("news_count", 0)} 条新闻
                </div>
                {news_list_html}
            </div>
            <div class="analyst-card" style="margin-top:15px;">
                <h4>社交媒体情绪</h4>
                <ul>
                    {social_html}
                </ul>
            </div>
        </div>

        <!-- 多头分析师观点 -->
        <div class="section">
            <h2>多头分析师观点</h2>
            <div class="analyst-card">
                <h4>买入论证</h4>
                <ul>
                    {"".join(f"<li>{ReportGenerator._render_markdown(point)}</li>" for point in parallel.get("bull_analyst", {}).get("analysis", ["待分析"]))}
                </ul>
            </div>
        </div>

        <!-- 空头分析师观点 -->
        <div class="section">
            <h2>空头分析师观点</h2>
            <div class="analyst-card">
                <h4>卖出/观望论证</h4>
                <ul>
                    {"".join(f"<li>{ReportGenerator._render_markdown(point)}</li>" for point in parallel.get("bear_analyst", {}).get("analysis", ["待分析"]))}
                </ul>
            </div>
        </div>

        <!-- 技术分析 -->
        <div class="section">
            <h2>技术分析</h2>
            <div class="analyst-card">
                <h4>技术指标解读</h4>
                {tech_html}
            </div>
        </div>

        <!-- 基本面分析 -->
        <div class="section">
            <h2>基本面分析</h2>
            <div class="analyst-card">
                <h4>估值与财务指标</h4>
                {fund_html}
            </div>
        </div>

        <!-- 风险评估 -->
        <div class="section">
            <h2>风险评估</h2>
            <table class="risk-table">
                <tr>
                    <th>情景</th>
                    <th>仓位</th>
                    <th>预期收益</th>
                    <th>止损</th>
                </tr>
                <tr>
                    <td>{risk["aggressive"].get("position", "激进派")}</td>
                    <td>{risk["aggressive"].get("position_size", "获取数据失败") if not risk.get("_risk_debate_failed") else "获取数据失败"}</td>
                    <td>{risk["aggressive"].get("target_return", "获取数据失败") if not risk.get("_risk_debate_failed") else "获取数据失败"}</td>
                    <td>{risk["aggressive"].get("stop_loss", "获取数据失败") if not risk.get("_risk_debate_failed") else "获取数据失败"}</td>
                </tr>
                <tr>
                    <td>{risk["neutral"].get("position", "中性派")}</td>
                    <td>{risk["neutral"].get("position_size", "获取数据失败") if not risk.get("_risk_debate_failed") else "获取数据失败"}</td>
                    <td>{risk["neutral"].get("target_return", "获取数据失败") if not risk.get("_risk_debate_failed") else "获取数据失败"}</td>
                    <td>{risk["neutral"].get("stop_loss", "获取数据失败") if not risk.get("_risk_debate_failed") else "获取数据失败"}</td>
                </tr>
                <tr>
                    <td>{risk["conservative"].get("position", "保守派")}</td>
                    <td>{risk["conservative"].get("position_size", "获取数据失败") if not risk.get("_risk_debate_failed") else "获取数据失败"}</td>
                    <td>{risk["conservative"].get("target_return", "获取数据失败") if not risk.get("_risk_debate_failed") else "获取数据失败"}</td>
                    <td>{risk["conservative"].get("stop_loss", "获取数据失败") if not risk.get("_risk_debate_failed") else "获取数据失败"}</td>
                </tr>
            </table>
        </div>

        <!-- 风险因素 -->
        <div class="section">
            <h2>风险因素</h2>
            <ul>
                {"".join(f"<li>{k}: {v}</li>" for k, v in final["risk_assessment"].items())}
            </ul>
            <p style="margin-top:12px;"><strong>监控要点:</strong></p>
            <ul>
                {"".join(f"<li>{ReportGenerator._render_markdown(point)}</li>" for point in final["monitoring_points"])}
            </ul>
            <p style="margin-top:12px;"><strong>适合投资者:</strong> {", ".join(final["suitable_investors"])}</p>
        </div>

        <!-- 辩论过程 -->
        <div class="section">
            <h2>辩论过程</h2>
            {debate_html}
        </div>

        <!-- 免责声明 -->
        <div class="disclaimer">
            <strong>免责声明:</strong><br>
            本报告由 AI 多智能体系统自动生成，基于公开信息和算法模型分析。
            本报告仅供研究和学习目的，不构成任何形式的投资建议或邀约。
            投资有风险，入市需谨慎。过去的表现不代表未来的收益。
            请在做出任何投资决策前，咨询专业的金融顾问。
        </div>

        <div class="footer">
            <p>Generated by TradingAgents-CN Skill</p>
            <p>本报告版权归属分析者所有，保留所有权利</p>
        </div>
    </div>
</body>
</html>"""

        return html

    def _html_to_pdf(self, html_content: str, output_path: Path):
        """将 HTML 转换为 PDF"""
        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(output_path)
            return
        except ImportError:
            pass

        try:
            import subprocess
            import tempfile

            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_html = f.name

            subprocess.run(
                ['wkhtmltopdf', '--page-size', 'A4', '--margin-top', '15mm',
                 '--margin-bottom', '15mm', '--margin-left', '12mm', '--margin-right', '12mm',
                 temp_html, str(output_path)],
                check=True
            )
            os.unlink(temp_html)
            return
        except (ImportError, subprocess.CalledProcessError, FileNotFoundError):
            pass

        html_path = output_path.with_suffix('.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        raise RuntimeError(
            f"PDF 生成失败（weasyprint 和 wkhtmltopdf 均不可用）。"
            f"HTML 报告已保存至: {html_path}"
        )


if __name__ == "__main__":
    from analyst_multi import StockAnalyst

    # 测试带真实新闻数据
    analyst = StockAnalyst()
    news_data = [
        {"title": "苹果发布 Q4 财报，营收超预期", "date": "2024-11-01", "source": "彭博", "summary": "苹果公司第四季度营收同比增长 8.1%，iPhone 销量强劲", "sentiment": "偏多"},
        {"title": "iPhone 16 销量创历史新高", "date": "2024-10-28", "source": "路透", "summary": "新一代 iPhone 需求旺盛，出货量超预期 20%", "sentiment": "偏多"},
        {"title": "欧盟对苹果处以 18 亿欧元罚款", "date": "2024-10-25", "source": "BBC", "summary": "因 App Store 垄断行为被欧盟罚款", "sentiment": "偏空"},
    ]
    result = analyst.analyze(
        stock_code="AAPL",
        text_description="苹果公司 Q4 财报分析",
        news_data=news_data
    )

    generator = ReportGenerator()
    pdf_path = generator.generate(result)
    print(f"PDF 报告已生成: {pdf_path}")
