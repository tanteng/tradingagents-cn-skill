#!/usr/bin/env python3
"""
PDF Report Generator for Stock Analysis
生成专业股票分析报告 PDF
"""

import os
import re
import json
import markdown
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class ReportGenerator:
    """股票分析报告 PDF 生成器"""

    # 英文 JSON key → 中文显示名称映射表
    # prompt 要求 JSON key 用英文保证 LLM 稳定性，PDF 渲染时转为中文
    KEY_CN_MAP = {
        # 技术分析 indicators
        "trend_direction": "趋势方向",
        "support": "支撑位",
        "resistance": "阻力位",
        "RSI": "RSI",
        "MACD_signal": "MACD信号",
        "MACD_histogram": "MACD柱状图",
        "KDJ": "KDJ",
        "ma_alignment": "均线排列",
        "volume_pattern": "成交量形态",
        "bollinger_position": "布林带位置",
        # 操作建议 trade_advice
        "stop_loss": "止损位",
        "entry_point": "入场点",
        "take_profit": "止盈位",
        "position_size": "仓位建议",
        # 交易计划 trading_plan
        "decision": "操作决策",
        "buy_price": "买入价格",
        "target_price": "目标价格",
        "reference_price": "参考价格",
        "reference_target": "参考目标价",
        "reference_stop": "参考止损价",
        "entry_criteria": "入场条件",
        "exit_criteria": "出场条件",
        # 风险评估 risk_assessment
        "market_risk": "市场风险",
        "liquidity_risk": "流动性风险",
        "volatility_risk": "波动性风险",
        "policy_risk": "政策风险",
        "industry_risk": "行业风险",
        "credit_risk": "信用风险",
        "concentration_risk": "集中度风险",
        "systematic_risk": "系统性风险",
        "operational_risk": "运营风险",
        # 基本面 indicators（大小写都映射，LLM 输出不一定统一）
        "PE": "PE（市盈率）",
        "PB": "PB（市净率）",
        "ROE": "ROE（净资产收益率）",
        "EPS": "EPS（每股收益）",
        "pe": "PE（市盈率）",
        "pb": "PB（市净率）",
        "roe": "ROE（净资产收益率）",
        "eps": "EPS（每股收益）",
        "valuation": "估值水平",
        "revenue_growth": "营收增速",
        "gross_margin": "毛利率",
        "net_margin": "净利率",
        "debt_ratio": "资产负债率",
        "dividend_yield": "股息率",
        "free_cash_flow": "自由现金流",
        "profit_growth": "利润增速",
        "buy_rating_count": "买入评级数",
        "target_price": "目标价格",
        # 综合决策
        "rating": "评级",
        "risk_level": "风险等级",
        "investment_horizon": "投资期限",
        "recommendation": "投资建议",
        "executive_summary": "执行摘要",
        "investment_thesis": "投资逻辑",
        "signal_summary": "信号总结",
    }

    @classmethod
    def _cn_key(cls, key: str) -> str:
        """将英文 key 转为中文显示名称，无映射则原样返回"""
        return cls.KEY_CN_MAP.get(key, key)

    def __init__(self):
        self.output_dir = Path(__file__).parent / "reports"
        self.output_dir.mkdir(exist_ok=True)

    @staticmethod
    def _render_markdown(text: str) -> str:
        """把 Markdown 转为 HTML，智能处理 LLM 常见输出格式"""
        if not text:
            return ""

        # 0. 处理字面量转义换行符（LLM 常见输出问题）
        text = text.replace("\\n\\n", "\n\n").replace("\\n", "\n")
        text = text.replace("\\t", "\t")

        # 1. 清理 ```json 代码块包裹
        if text.strip().startswith('```'):
            lines = text.strip().split('\n')
            # 去掉第一行的 ```json 或 ```
            if lines[0].strip().startswith('```'):
                lines = lines[1:]
            # 去掉最后一行的 ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            text = '\n'.join(lines).strip()

        # 2. 如果是 JSON 对象，提取可读文本
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                import json as _json
                obj = _json.loads(stripped)
                if isinstance(obj, dict):
                    # 优先取长文本字段
                    for field in ("debate_text", "report", "综合评价", "基本面总结",
                                  "executive_summary", "investment_thesis", "rationale",
                                  "full_text"):
                        val = obj.get(field, "")
                        if isinstance(val, str) and len(val) > 50:
                            text = val.replace("\\n\\n", "\n\n").replace("\\n", "\n")
                            break
                    else:
                        # 没有长文本字段，格式化输出所有内容
                        parts = []
                        for k, v in obj.items():
                            ck = ReportGenerator._cn_key(k)
                            if isinstance(v, str) and v:
                                parts.append(f"**{ck}**: {v}")
                            elif isinstance(v, list) and v:
                                parts.append(f"**{ck}**: " + "、".join(str(i) for i in v))
                            elif isinstance(v, dict) and v:
                                sub = "、".join(f"{ReportGenerator._cn_key(sk)}: {sv}" for sk, sv in v.items() if sv)
                                if sub:
                                    parts.append(f"**{ck}**: {sub}")
                        text = "\n\n".join(parts) if parts else str(obj)
            except:
                pass
        # 容错：修复未闭合的 ** 标记（文本截断时可能出现）
        if text.count('**') % 2 != 0:
            text += '**'
        # 容错：修复未闭合的 * 标记
        single_stars = len(re.findall(r'(?<!\*)\*(?!\*)', text))
        if single_stars % 2 != 0:
            text += '*'
        return markdown.markdown(text, extensions=['nl2br', 'tables', 'fenced_code'])

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
        stock_name = analysis_result.get("stock_name", "").split("(")[0].split("（")[0].strip()
        safe_name = re.sub(r"[^\w\u4e00-\u9fff]+", "_", stock_name).strip("_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if safe_name:
            filename = f"{stock_code}_{safe_name}_{timestamp}.pdf"
        else:
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

        # 0. 路径归一化：AI agent 可能把数据写到顶层而非标准嵌套路径，
        #    这里统一搬到标准路径，确保下游读取的确定性。
        _NORMALIZE_MAP = [
            # (顶层源 key,              标准嵌套路径)
            ("tech_analyst",             "parallel_analysis.tech_analyst"),
            ("fundamentals_analyst",     "parallel_analysis.fundamentals_analyst"),
            ("news_analyst",             "parallel_analysis.news_analyst"),
            ("bull_debate_r1",           "investment_debate.bull_r1"),
            ("bear_debate_r1",           "investment_debate.bear_r1"),
            ("bull_debate_r2",           "investment_debate.bull_r2"),
            ("bear_debate_r2",           "investment_debate.bear_r2"),
        ]
        for src_key, dst_path in _NORMALIZE_MAP:
            src_val = result.get(src_key)
            if not src_val or not isinstance(src_val, dict):
                continue
            # 解析 dst_path（最多两级：parent.child）
            parts = dst_path.split(".")
            parent_key, child_key = parts[0], parts[1]
            parent = result.setdefault(parent_key, {})
            # 仅当标准路径为空时才搬入
            if not parent.get(child_key):
                parent[child_key] = src_val

        # 1. 修复新闻摘要
        news_analyst = result.get("parallel_analysis", {}).get("news_analyst", {})
        # schema: news_list 在顶层 news_data 下，注入到 news_analyst
        if not news_analyst.get("news_list"):
            _nd = result.get("news_data", {})
            if isinstance(_nd, dict) and _nd.get("news_list"):
                news_analyst["news_list"] = _nd["news_list"]
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


    def _render_bull_bear_section(self, result, side):
        """按 schema 渲染多头/空头观点。
        
        schema: investment_debate.{side}_r{1,2} 是 dict，含 debate_text (string)。
        """
        inv = result.get("investment_debate", {})
        r1 = self._extract_debate_text(inv.get(f"{side}_r1", {}))
        r2 = self._extract_debate_text(inv.get(f"{side}_r2", {}))
        
        parts = []
        if r1:
            parts.append(f"<h4>Round 1</h4>{self._render_markdown(r1)}")
        if r2:
            parts.append(f"<h4>Round 2</h4>{self._render_markdown(r2)}")
        
        return "\n".join(parts) if parts else "<p>待分析</p>"


    @staticmethod
    def _extract_debate_text(raw):
        """按 schema 从辩论对象中读取 debate_text。
        
        schema 约定: 辩论输出是 dict，必含 debate_text (string)。
        """
        if not raw:
            return ""
        if isinstance(raw, dict):
            return raw.get("debate_text", "")
        return str(raw)
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
            news_list_html = '<div class="no-news">暂无新闻数据</div>'

        # 聚合新闻情绪：优先取 news_analyst 顶层 sentiment，否则从 news_list 统计
        _news_sentiment = news_analyst.get("sentiment", "")
        if not _news_sentiment:
            _sentiments = [n.get("sentiment", "") for n in news_analyst.get("news_list", []) if n.get("sentiment")]
            if _sentiments:
                from collections import Counter
                _cnt = Counter(_sentiments)
                _top = _cnt.most_common(1)[0]
                _news_sentiment = f"{_top[0]}（{_top[1]}/{len(_sentiments)}条）"
            else:
                _news_sentiment = "暂无数据"

        # 生成技术分析 HTML
        tech_analyst_data = parallel.get("tech_analyst", {})
        ta = tech_analyst_data.get("technical_analysis", {})

        # 兼容两种数据结构：
        # 结构A（嵌套）: tech_analyst.technical_analysis.趋势判断 / .关键指标 / .操作建议
        # 结构B（扁平）: tech_analyst.indicators / .操作建议 / .技术信号总结
        trend = ta.get("趋势判断", {})
        nested_indicators = ta.get("关键指标", {})
        advice = ta.get("trade_advice", {}) or tech_analyst_data.get("trade_advice", {})
        flat_indicators = tech_analyst_data.get("indicators", {})
        tech_summary = (
            ta.get("signal_summary", "")
            or tech_analyst_data.get("signal_summary", "")
            or (tech_analyst_data.get("analysis", [""])[0] if tech_analyst_data.get("analysis") else "")
        )

        # 合并 indicators：优先用嵌套结构，扁平结构兜底
        all_indicators = nested_indicators or flat_indicators

        tech_html = "<ul>"
        has_data = False

        if trend and isinstance(trend, dict):
            tech_html += "<li><strong>趋势判断：</strong> "
            tech_html += " / ".join(f"{self._cn_key(k)}: {v}" for k, v in trend.items() if v)
            tech_html += "</li>"
            has_data = True

        if all_indicators and isinstance(all_indicators, dict):
            tech_html += "<li><strong>关键指标：</strong></li>"
            for k, v in all_indicators.items():
                tech_html += f'<li style="margin-left:16px">{self._cn_key(k)}: {v}</li>'
            has_data = True

        if advice and isinstance(advice, dict):
            tech_html += "<li><strong>操作建议：</strong></li>"
            for k, v in advice.items():
                tech_html += f'<li style="margin-left:16px">{self._cn_key(k)}: {v}</li>'
            has_data = True

        if tech_summary:
            tech_html += f"<li><strong>技术信号：</strong>{tech_summary}</li>"
            has_data = True

        tech_html += "</ul>"

        # 渲染 report 长文本（技术分析的完整报告）
        tech_report = tech_analyst_data.get("report", "")
        if tech_report and len(tech_report) > 50:
            tech_html += f'<div style="margin-top:12px;font-size:11px;line-height:1.6;background:#f9f9f9;padding:12px;border-radius:8px;">{self._render_markdown(tech_report)}</div>'
            has_data = True

        if not has_data:
            tech_html = "<ul><li>待分析</li></ul>"

        # 生成基本面分析 HTML
        fund_analyst_data = parallel.get("fundamentals_analyst", {})
        # schema: financials 是确定字段（pe/pb/roe/gross_margin/net_margin/revenue_growth/debt_ratio）
        fa = fund_analyst_data.get("financials", {})
        if not isinstance(fa, dict):
            fa = {}
        # 从 report 文本提取估值数据填充 N/A 字段
        _rpt = fund_analyst_data.get("report", "")
        if isinstance(_rpt, str) and len(_rpt) > 50:
            _rpt_clean = re.sub(r'```\w*\n?', '', _rpt).replace('```', '')
            def _xtr(text, pats):
                for p in pats:
                    m = re.search(p, text, re.IGNORECASE)
                    if m: return m.group(1).strip()
                return None
            _extracts = {
                "PE": _xtr(_rpt_clean, [r'PE[（(TTM)]*[）)]?[：:≈约为\s]*([\d.]+|亏损|负值|N/A)', r'市盈率[：:≈约为\s]*([\d.]+|亏损)']),
                "PB": _xtr(_rpt_clean, [r'PB[：:≈约为\s]*([\d.]+)', r'市净率[：:≈约为\s]*([\d.]+)']),
                "ROE": _xtr(_rpt_clean, [r'ROE[：:≈约为\s]*([\-\d.]+%?)', r'净资产收益率[：:≈约为\s]*([\-\d.]+%?)']),
                "revenue_growth": _xtr(_rpt_clean, [r'营收[同比]*增[速长率][：:≈约为\s]*([\d.]+%)', r'revenue.{0,10}grew?[：:≈约为\s]*([\d.]+%)']),
                "gross_margin": _xtr(_rpt_clean, [r'毛利率[：:≈约为\s]*([\d.]+%)', r'[Gg]ross [Mm]argin[：:≈约为\s]*([\d.]+%)']),
                "net_margin": _xtr(_rpt_clean, [r'净利[润率][率]?[：:≈约为\s]*([\-\d.]+%)', r'[Nn]et [Mm]argin[：:≈约为\s]*([\-\d.]+%)']),
                "debt_ratio": _xtr(_rpt_clean, [r'负债率[：:≈约为\s]*([\d.]+%)', r'资产负债率[：:≈约为\s]*([\d.]+%)']),
            }
            # 填充到 fa 嵌套结构中
            if isinstance(fa, dict):
                for sect_val in fa.values():
                    if isinstance(sect_val, dict):
                        for k in list(sect_val.keys()):
                            if sect_val[k] in ("N/A", "", None) and k in _extracts and _extracts[k] and _extracts[k] != "N/A":
                                sect_val[k] = _extracts[k]
                # 也填充到 fa 顶层
                for k, v in _extracts.items():
                    if v and v != "N/A" and fa.get(k) in ("N/A", "", None):
                        fa[k] = v
        valuation = fa.get("估值分析", {})
        profitability = fa.get("盈利能力", {})
        growth = fa.get("成长性", {})
        health = fa.get("财务健康", {})
        # 综合评价：先从结构化字段取，再从 report 文本中提取
        fund_summary = fa.get("综合评价", "") or fa.get("fundamental_rating", "") or fund_analyst_data.get("fundamental_rating", "")
        if not fund_summary:
            # report 可能是 ```json {"report": "..."} ``` 嵌套格式
            _raw_report = fund_analyst_data.get("report", "")
            if isinstance(_raw_report, str) and _raw_report:
                _cleaned = re.sub(r'^```\w*\s*', '', _raw_report.strip())
                _cleaned = re.sub(r'```\s*$', '', _cleaned.strip())
                if _cleaned.startswith('{'):
                    try:
                        _parsed = json.loads(_cleaned)
                        if isinstance(_parsed, dict):
                            fund_summary = _parsed.get("report", "") or _parsed.get("综合评价", "") or _parsed.get("fundamental_rating", "")
                    except:
                        # JSON 解析失败，尝试手工提取 report 字段的值
                        _m = re.search(r'"report"\s*:\s*"(.*?)(?:"\s*[,}])', _cleaned[:5000], re.DOTALL)
                        if _m:
                            fund_summary = _m.group(1).replace('\\n', '\n').replace('\\"', '"')
                if not fund_summary:
                    fund_summary = _cleaned[:500]
        if not fund_summary:
            fund_summary = (fund_analyst_data.get("analysis", [""])[0] if fund_analyst_data.get("analysis") else "待分析")
        fund_summary = self._render_markdown(fund_summary) if fund_summary else "待分析"

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
        # 当嵌套结构（估值分析/盈利能力/成长性/财务健康）全为空时，
        # 回退到 financials 扁平结构或 indicators + report 文本
        if not valuation and not profitability and not growth and not health:
            # financials 可能是扁平 dict（如 {pe, pb, roe, gross_margin...}），直接渲染
            _flat_fin = {k: v for k, v in fa.items() if not isinstance(v, dict) and v and v != "N/A"}
            indicators = fund_analyst_data.get("indicators", {})
            _data = _flat_fin or (indicators if isinstance(indicators, dict) else {})
            if _data:
                fund_html = "<ul>"
                fund_html += "<li><strong>关键指标：</strong></li>"
                for k, v in _data.items():
                    fund_html += f'<li style="margin-left:16px">{self._cn_key(k)}: {v}</li>'
                # 估值总结
                _val_summary = fa.get("估值总结", "") or fund_analyst_data.get("估值总结", "")
                if _val_summary:
                    fund_html += f'<li><strong>估值总结：</strong>{_val_summary}</li>'
                if fund_summary:
                    fund_html += f"<li><strong>综合评价：</strong>{fund_summary}</li>"
            else:
                fund_html = "<ul><li>待分析</li>"
        fund_html += "</ul>"

        # 生成辩论 HTML
        debate_html = ""
        debate_rounds = []
        _inv_debate = result.get("investment_debate", {})
        if _inv_debate.get("bull_r1") or _inv_debate.get("bear_r1"):
            debate_rounds = [{"bull": self._extract_debate_text(_inv_debate.get("bull_r1", "")), "bear": self._extract_debate_text(_inv_debate.get("bear_r1", ""))}]
            if _inv_debate.get("bull_r2") or _inv_debate.get("bear_r2"):
                debate_rounds.append({"bull": self._extract_debate_text(_inv_debate.get("bull_r2", "")), "bear": self._extract_debate_text(_inv_debate.get("bear_r2", ""))})
        if not debate_rounds:
            debate_rounds = result.get("debate", {}).get("rounds", [])
        # 兼容：如果 rounds 中的 bull/bear 是纯文本字符串，直接渲染
        _has_text_debate = debate_rounds and isinstance(debate_rounds[0].get("bull", ""), str) and len(debate_rounds[0].get("bull", "")) > 50
        if _has_text_debate:
            # 纯文本模式：纯文本辩论，直接渲染
            for i, r in enumerate(debate_rounds):
                round_num = r.get("round", i + 1)
                bull_text = r.get("bull", "")
                bear_text = r.get("bear", "")
                bull_html_content = self._render_markdown(bull_text) if bull_text else "<p>待补充</p>"
                bear_html_content = self._render_markdown(bear_text) if bear_text else "<p>待补充</p>"
                debate_html += f"""
                <div class="debate-round">
                    <h4 class="debate-round-title">第{round_num}轮辩论</h4>
                    <div class="debate-columns">
                        <div class="debate-column bull">
                            <div class="debate-column-header">🐂 多方论点</div>
                            <div style="font-size:11px;line-height:1.6;padding:8px;">{bull_html_content}</div>
                        </div>
                        <div class="debate-column bear">
                            <div class="debate-column-header">🐻 空方论点</div>
                            <div style="font-size:11px;line-height:1.6;padding:8px;">{bear_html_content}</div>
                        </div>
                    </div>
                </div>
                """
        elif debate_rounds:
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
        body {{ font-family: "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", "SimHei", sans-serif; line-height: 1.6; color: #333; font-size: 12px; }}
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
                <div>分析框架: TradingAgents-CN Skill</div>
            </div>
        </div>

        <!-- 执行摘要 -->
        <div class="section">
            <h2>执行摘要</h2>
            <div class="decision-box">
                <div class="big">{final.get("rating", final.get("final_recommendation", "持有"))}</div>
                <div class="sub">风险等级: {final["risk_level"]} | 投资期限: {final["investment_horizon"]}</div>
            </div>
            <p><strong>核心逻辑:</strong></p>{self._render_markdown(manager.get("rationale", ""))}
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
            <p><strong>仓位建议:</strong> {'<span style="color:#c62828">数据获取失败</span>' if trading.get('_position_size_failed') else (trading.get('position_size', '') + '（观望中）' if trading.get('decision') in ('观望', '卖出') and trading.get('position_size') == '0%' else trading.get('position_size', ''))}
</p>
            <p><strong>入场条件:</strong> {trading.get("entry_criteria", "")}</p>
            <p><strong>出场条件:</strong> {'<span style="color:#c62828">数据获取失败</span>' if trading.get('_exit_criteria_failed') else (trading.get('exit_criteria', '') + '（当前为观望状态）' if trading.get('exit_criteria') == '不适用' else trading.get('exit_criteria', ''))}
</p>
        </div>

        <!-- 新闻分析 -->
        <div class="section">
            <h2>新闻分析</h2>
            <div class="news-section">
                <div class="sentiment-summary">
                    <strong>新闻情绪:</strong> {_news_sentiment} | 共 {len(news_analyst.get("news_list", []))} 条新闻
                </div>
                {news_list_html}
            </div>
        </div>

        <!-- 多头分析师观点 -->
        <div class="section">
            <h2>多头分析师观点</h2>
            <div class="analyst-card">
                <h4>买入论证</h4>
                <ul>
                    {self._render_bull_bear_section(result, "bull")}
                </ul>
            </div>
        </div>

        <!-- 空头分析师观点 -->
        <div class="section">
            <h2>空头分析师观点</h2>
            <div class="analyst-card">
                <h4>卖出/观望论证</h4>
                <ul>
                    {self._render_bull_bear_section(result, "bear")}
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
                    <td>{(risk["aggressive"].get("position_size", "详见辩论") if isinstance(risk.get("aggressive"), dict) else "详见辩论") if not risk.get("_risk_debate_failed") else "详见辩论"}</td>
                    <td>{(risk["aggressive"].get("target_return", "详见辩论") if isinstance(risk.get("aggressive"), dict) else "详见辩论") if not risk.get("_risk_debate_failed") else "详见辩论"}</td>
                    <td>{(risk["aggressive"].get("stop_loss", "详见辩论") if isinstance(risk.get("aggressive"), dict) else "详见辩论") if not risk.get("_risk_debate_failed") else "详见辩论"}</td>
                </tr>
                <tr>
                    <td>{risk["neutral"].get("position", "中性派")}</td>
                    <td>{(risk["neutral"].get("position_size", "详见辩论") if isinstance(risk.get("neutral"), dict) else "详见辩论") if not risk.get("_risk_debate_failed") else "详见辩论"}</td>
                    <td>{(risk["neutral"].get("target_return", "详见辩论") if isinstance(risk.get("neutral"), dict) else "详见辩论") if not risk.get("_risk_debate_failed") else "详见辩论"}</td>
                    <td>{(risk["neutral"].get("stop_loss", "详见辩论") if isinstance(risk.get("neutral"), dict) else "详见辩论") if not risk.get("_risk_debate_failed") else "详见辩论"}</td>
                </tr>
                <tr>
                    <td>{risk["conservative"].get("position", "保守派")}</td>
                    <td>{(risk["conservative"].get("position_size", "详见辩论") if isinstance(risk.get("conservative"), dict) else "详见辩论") if not risk.get("_risk_debate_failed") else "详见辩论"}</td>
                    <td>{(risk["conservative"].get("target_return", "详见辩论") if isinstance(risk.get("conservative"), dict) else "详见辩论") if not risk.get("_risk_debate_failed") else "详见辩论"}</td>
                    <td>{(risk["conservative"].get("stop_loss", "详见辩论") if isinstance(risk.get("conservative"), dict) else "详见辩论") if not risk.get("_risk_debate_failed") else "详见辩论"}</td>
                </tr>
            </table>
        </div>

        <!-- 风控辩论详情 -->
        <div class="section">
            <h2>风控辩论详情</h2>
            <div style="margin-bottom:15px;">
                <h4 style="color:#c62828;">🔴 激进型分析师</h4>
                <div style="font-size:11px;line-height:1.6;background:#fff5f5;padding:12px;border-radius:8px;border-left:3px solid #c62828;">
                    {self._render_markdown(self._extract_debate_text(risk.get("aggressive", "")))}
                </div>
            </div>
            <div style="margin-bottom:15px;">
                <h4 style="color:#2e7d32;">🟢 保守型分析师</h4>
                <div style="font-size:11px;line-height:1.6;background:#f5fff5;padding:12px;border-radius:8px;border-left:3px solid #2e7d32;">
                    {self._render_markdown(self._extract_debate_text(risk.get("conservative", "")))}
                </div>
            </div>
            <div style="margin-bottom:15px;">
                <h4 style="color:#f57c00;">🟡 中立型分析师</h4>
                <div style="font-size:11px;line-height:1.6;background:#fffde7;padding:12px;border-radius:8px;border-left:3px solid #f57c00;">
                    {self._render_markdown(self._extract_debate_text(risk.get("neutral", {})))}
                </div>
            </div>
        </div>

        <!-- 风险因素 -->
        <div class="section">
            <h2>风险因素</h2>
            <ul>
                {"".join(f"<li>{ReportGenerator._cn_key(k)}: {v}</li>" for k, v in final["risk_assessment"].items())}
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
            本报告由 TradingAgents-CN Skill自动生成，基于公开信息和算法模型分析。
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
        """将 HTML 转换为 PDF。
        macOS: Chrome headless 优先（解决 weasyprint 字体嵌入乱码）
        其他平台: weasyprint 优先（服务器环境更轻量）
        """
        import platform
        import subprocess
        import tempfile

        is_macos = platform.system() == "Darwin"

        if is_macos:
            # macOS: Chrome headless 优先（weasyprint 在 macOS 上字体嵌入有乱码问题）
            if self._try_chrome_headless(html_content, output_path):
                return
            # macOS fallback: weasyprint
            if self._try_weasyprint(html_content, output_path):
                return
        else:
            # Linux/其他: weasyprint 优先（服务器上有 Noto CJK 字体，渲染正常）
            if self._try_weasyprint(html_content, output_path):
                return
            # Linux fallback: Chrome headless
            if self._try_chrome_headless(html_content, output_path):
                return

        # 最终 fallback: wkhtmltopdf
        if self._try_wkhtmltopdf(html_content, output_path):
            return

        # 所有引擎都不可用: 保存 HTML
        html_path = output_path.with_suffix('.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        raise RuntimeError(
            f"PDF 生成失败（Chrome/weasyprint/wkhtmltopdf 均不可用）。"
            f"HTML 报告已保存至: {html_path}"
        )

    @staticmethod
    def _try_chrome_headless(html_content: str, output_path: Path) -> bool:
        """尝试用 Chrome headless 生成 PDF。成功返回 True。"""
        import subprocess
        import tempfile

        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
        ]
        for chrome in chrome_paths:
            temp_html = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.html', delete=False, encoding='utf-8'
                ) as f:
                    f.write(html_content)
                    temp_html = f.name

                subprocess.run(
                    [
                        chrome, "--headless", "--disable-gpu", "--no-sandbox",
                        "--run-all-compositor-stages-before-draw",
                        f"--print-to-pdf={output_path}",
                        "--print-to-pdf-no-header",
                        "--no-pdf-header-footer",
                        f"file://{temp_html}",
                    ],
                    capture_output=True,
                    timeout=60,
                )
                if output_path.exists() and output_path.stat().st_size > 0:
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass
            finally:
                if temp_html:
                    try:
                        os.unlink(temp_html)
                    except OSError:
                        pass
        return False

    @staticmethod
    def _try_weasyprint(html_content: str, output_path: Path) -> bool:
        """尝试用 weasyprint 生成 PDF。成功返回 True。"""
        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(output_path)
            return True
        except (ImportError, Exception):
            return False

    @staticmethod
    def _try_wkhtmltopdf(html_content: str, output_path: Path) -> bool:
        """尝试用 wkhtmltopdf 生成 PDF。成功返回 True。"""
        import subprocess
        import tempfile

        temp_html = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.html', delete=False, encoding='utf-8'
            ) as f:
                f.write(html_content)
                temp_html = f.name

            subprocess.run(
                ['wkhtmltopdf', '--page-size', 'A4', '--margin-top', '15mm',
                 '--margin-bottom', '15mm', '--margin-left', '12mm', '--margin-right', '12mm',
                 temp_html, str(output_path)],
                check=True,
                capture_output=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            return False
        finally:
            if temp_html:
                try:
                    os.unlink(temp_html)
                except OSError:
                    pass


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
