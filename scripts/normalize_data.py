#!/usr/bin/env python3
"""
normalize_data.py — 在 pdf_generator.py 的 _generate_html 开头调用
将 full_report.json 的实际结构规范化为渲染代码期望的格式

这不是 adapt_data.py 那种"猜格式"的适配层，而是基于确定的 JSON schema 做映射。
"""

import json
import re


def normalize(data: dict) -> dict:
    """将 full_report.json 规范化为 pdf_generator 的渲染格式"""

    result = {
        "stock_code": data.get("stock_code", "UNKNOWN"),
        "stock_name": data.get("stock_name", "未知"),
        "current_price": data.get("current_price"),
        "timestamp": data.get("timestamp", ""),
    }

    # ===== parallel_analysis =====
    pa = data.get("parallel_analysis", {})

    # tech_analyst: 直接透传，key 已确定
    result.setdefault("parallel_analysis", {})["tech_analyst"] = pa.get("tech_analyst", {})

    # fundamentals_analyst: financials 用英文 key，映射为渲染期望的中文展示
    fa = pa.get("fundamentals_analyst", {})
    financials = fa.get("financials", {})
    fa["fundamentals_analysis"] = {
        "估值分析": {"PE": financials.get("pe", "N/A"), "PB": financials.get("pb", "N/A")},
        "盈利能力": {
            "ROE": financials.get("roe", "N/A"),
            "净利率": financials.get("net_margin", "N/A"),
            "毛利率": financials.get("gross_margin", "N/A"),
        },
        "成长性": {"营收增速": financials.get("revenue_growth", "N/A")},
        "财务健康": {"负债率": financials.get("debt_ratio", "N/A")},
        "综合评价": fa.get("valuation_summary", ""),
    }
    # report 字段：清理可能的 json 代码块包裹
    report_text = fa.get("report", "")
    if isinstance(report_text, str) and report_text.strip().startswith("```"):
        lines = report_text.strip().split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        # 如果整体是 JSON，提取 report 字段
        cleaned = "\n".join(lines).strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "report" in parsed:
                report_text = parsed["report"]
                # 同时填充 financials
                if "financials" in parsed and isinstance(parsed["financials"], dict):
                    for k, v in parsed["financials"].items():
                        if k not in financials or financials[k] in ("N/A", "", None):
                            financials[k] = v
                    # 重新映射
                    fa["fundamentals_analysis"]["估值分析"]["PE"] = financials.get("pe", "N/A")
                    fa["fundamentals_analysis"]["估值分析"]["PB"] = financials.get("pb", "N/A")
                    fa["fundamentals_analysis"]["盈利能力"]["ROE"] = financials.get("roe", "N/A")
                    fa["fundamentals_analysis"]["盈利能力"]["净利率"] = financials.get("net_margin", "N/A")
                    fa["fundamentals_analysis"]["盈利能力"]["毛利率"] = financials.get("gross_margin", "N/A")
                    fa["fundamentals_analysis"]["成长性"]["营收增速"] = financials.get("revenue_growth", "N/A")
                    fa["fundamentals_analysis"]["财务健康"]["负债率"] = financials.get("debt_ratio", "N/A")
        except (json.JSONDecodeError, TypeError):
            report_text = cleaned
    fa["report"] = report_text
    fa["基本面总结"] = fa.get("valuation_summary", "") or fa.get("fundamental_rating", "")
    result["parallel_analysis"]["fundamentals_analyst"] = fa

    # news_analyst: 注入 news_list
    na = pa.get("news_analyst", {})
    news_data = data.get("news_data", {})

    # 从多个可能的来源查找 news_list
    news_list = (
        na.get("news_list")  # 来源1: news_analyst 自带
        or news_data.get("news_list")  # 来源2: 顶层 news_data
        or data.get("news_list")  # 来源3: 顶层 news_list（Agent 可能直接放这里）
        or []
    )
    # 如果 news_list 是字典形式的包装（Agent 有时输出 {"news_list": [...]}）
    if isinstance(news_data, dict) and not news_list:
        for v in news_data.values():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and "title" in v[0]:
                news_list = v
                break

    na["news_list"] = news_list
    na["news_count"] = len(news_list)
    if not na.get("platforms"):
        na["platforms"] = {"新闻": {"sentiment": na.get("新闻情绪", na.get("sentiment", "中性"))}}
    result["parallel_analysis"]["news_analyst"] = na

    # social_analyst: 直接透传
    result["parallel_analysis"]["social_analyst"] = pa.get("social_analyst", {})

    # ===== investment_debate → debate (渲染期望的格式) =====
    inv_debate = data.get("investment_debate", {})
    rounds = []

    # 从 JSON 结构中提取（新 Prompt 输出 JSON）
    def _extract_debate_text(val):
        """从辩论输出中提取文本，兼容 JSON dict 和纯文本"""
        if isinstance(val, dict):
            return val.get("debate_text", json.dumps(val, ensure_ascii=False))
        return str(val) if val else ""

    bull_r1 = _extract_debate_text(inv_debate.get("bull_r1", ""))
    bear_r1 = _extract_debate_text(inv_debate.get("bear_r1", ""))
    bull_r2 = _extract_debate_text(inv_debate.get("bull_r2", ""))
    bear_r2 = _extract_debate_text(inv_debate.get("bear_r2", ""))

    if bull_r1 or bear_r1:
        rounds.append({"bull": bull_r1, "bear": bear_r1})
    if bull_r2 or bear_r2:
        rounds.append({"bull": bull_r2, "bear": bear_r2})

    # bull/bear 分析数据（供 PDF 顶部的多空分析区域）
    def _extract_bull_bear(val, role):
        if isinstance(val, dict):
            case_key = "bull_case" if role == "bull" else "bear_case"
            return {
                "core_logic": val.get("core_logic", ""),
                "analysis": val.get(case_key, []),
                "confidence": val.get("confidence", 0.5),
            }
        # 纯文本 fallback
        return {"core_logic": str(val)[:200] if val else "待分析", "analysis": [], "confidence": 0.5}

    bull_data = _extract_bull_bear(inv_debate.get("bull_r1"), "bull")
    bear_data = _extract_bull_bear(inv_debate.get("bear_r1"), "bear")

    result["debate"] = {"rounds": rounds}
    result["parallel_analysis"]["bull_analyst"] = {
        "bull_detail": {"core_logic": bull_data["core_logic"], "bull_case": bull_data["analysis"]},
        "analysis": bull_data["analysis"] if bull_data["analysis"] else [bull_data["core_logic"]],
    }
    result["parallel_analysis"]["bear_analyst"] = {
        "bear_detail": {"core_logic": bear_data["core_logic"], "bear_case": bear_data["analysis"]},
        "analysis": bear_data["analysis"] if bear_data["analysis"] else [bear_data["core_logic"]],
    }

    # ===== manager_decision =====
    result["manager_decision"] = data.get("manager_decision", {})

    # ===== trading_plan =====
    result["trading_plan"] = data.get("trading_plan", {})

    # ===== risk_debate =====
    rd = data.get("risk_debate", {})
    adapted_risk = {}
    for role in ("aggressive", "conservative", "neutral"):
        val = rd.get(role, {})
        if isinstance(val, dict):
            # 新 JSON 格式（有 debate_text 字段）
            adapted_risk[role] = {
                "stance": val.get("stance", "待评估"),
                "points": val.get("key_points", []),
                "full_text": val.get("debate_text", ""),
                "position_size": val.get("position_size", "N/A"),
                "target_return": val.get("target_return", "N/A"),
                "stop_loss": val.get("stop_loss", "N/A"),
            }
        elif isinstance(val, str):
            # 旧纯文本 fallback
            adapted_risk[role] = {
                "stance": val[:100] if val else "待评估",
                "points": [],
                "full_text": val,
                "position_size": "详见辩论",
                "target_return": "详见辩论",
                "stop_loss": "详见辩论",
            }
    # 兼容 moderate
    if "neutral" in adapted_risk:
        adapted_risk["moderate"] = adapted_risk["neutral"]
    result["risk_debate"] = adapted_risk

    # ===== final_decision =====
    final = data.get("final_decision", {})
    if "rating" in final and "final_recommendation" not in final:
        final["final_recommendation"] = final["rating"]
    if "risk_assessment" not in final:
        final["risk_assessment"] = {
            "市场风险": "详见投资论文",
            "流动性风险": "详见投资论文",
            "波动性风险": "详见投资论文",
        }
    result["final_decision"] = final

    return result
