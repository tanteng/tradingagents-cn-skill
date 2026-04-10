#!/usr/bin/env python3
"""
adapt_data.py — 将 格式的分析数据转换为 v2 兼容格式

新增了：
- parallel_analysis 中的 report 字段（长文本）
- investment_debate（2轮辩论文本）
- risk_debate 中的纯文本（而非结构化 JSON）
- final_decision 中的五级评级（rating 字段）

本脚本将 数据映射为 v2 格式，供现有 pdf_generator.py 使用。

用法：
  echo '<JSON>' | python3 adapt_data.py
  python3 adapt_data.py --input v3_report.json
"""

import sys
import json
import argparse


def adapt_v3_to_v2(data: dict) -> dict:
    """将 数据结构适配为 v2 兼容格式"""

    result = {
        "stock_code": data.get("stock_code", "UNKNOWN"),
        "stock_name": data.get("stock_name", "未知"),
        "current_price": data.get("current_price"),
        "timestamp": data.get("timestamp", ""),
    }

    # ===== parallel_analysis 适配 =====
    pa = data.get("parallel_analysis", {})

    # 的分析师用 report 字段，v2 用各自不同的字段
    # tech_analyst
    tech = pa.get("tech_analyst", {})
    if "report" in tech:
        # 把 indicators 拆分为 v2 期望的子结构
        raw_indicators = tech.get("indicators", {})
        indicators_dict = {}
        if isinstance(raw_indicators, dict):
            for k, v in raw_indicators.items():
                indicators_dict[str(k)] = str(v) if v is not None else "N/A"
        # 操作建议
        raw_advice = tech.get("操作建议", {})
        advice_dict = {}
        if isinstance(raw_advice, dict):
            for k, v in raw_advice.items():
                advice_dict[str(k)] = str(v) if v is not None else "N/A"
        elif isinstance(raw_advice, str):
            advice_dict["操作建议"] = raw_advice
        # v2 technical_analysis 是 dict
        technical_analysis = {
            "趋势判断": {
                "整体趋势": tech.get("indicators", {}).get("趋势方向", "震荡"),
            },
            "关键指标": {
                "RSI": tech.get("indicators", {}).get("RSI", "N/A"),
                "MACD": tech.get("indicators", {}).get("MACD信号", "N/A"),
                "均线排列": tech.get("indicators", {}).get("均线排列", "N/A"),
                "成交量": tech.get("indicators", {}).get("成交量配合", "N/A"),
                "支撑位": tech.get("indicators", {}).get("支撑位", "N/A"),
                "压力位": tech.get("indicators", {}).get("压力位", "N/A"),
            },
            "操作建议": advice_dict,
            "技术信号总结": tech.get("技术信号总结", ""),
        }
        result_tech = {
            "report": tech.get("report", ""),
            "key_points": tech.get("key_points", []),
            "indicators": raw_indicators,
            "技术信号总结": tech.get("技术信号总结", ""),
            "操作建议": raw_advice,
            "technical_analysis": technical_analysis,
            "analysis": [tech.get("report", "")],
        }
    else:
        result_tech = tech

    # fundamentals_analyst
    fund = pa.get("fundamentals_analyst", {})
    if "report" in fund:
        raw_financials = fund.get("financials", {})
        fundamentals_analysis = {
            "估值分析": {
                "PE": raw_financials.get("PE", "N/A"),
                "PB": raw_financials.get("PB", "N/A"),
            },
            "盈利能力": {
                "ROE": raw_financials.get("ROE", "N/A"),
                "净利率": raw_financials.get("净利润增速", "N/A"),
                "毛利率": raw_financials.get("毛利率", "N/A"),
            },
            "成长性": {
                "营收增速": raw_financials.get("营收增速", "N/A"),
            },
            "财务健康": {
                "负债率": raw_financials.get("负债率", "N/A"),
            },
            "综合评价": fund.get("基本面总结", ""),
        }
        result_fund = {
            "report": fund.get("report", ""),
            "key_points": fund.get("key_points", []),
            "financials": raw_financials,
            "估值评估": fund.get("估值评估", ""),
            "基本面总结": fund.get("基本面总结", ""),
            "fundamentals_analysis": fundamentals_analysis,
            "analysis": [fund.get("report", "")],
        }
    else:
        result_fund = fund

    # news_analyst
    news = pa.get("news_analyst", {})
    if "report" in news:
        key_points = news.get("key_points", [])
        # 尝试从 news_list 字段获取新闻，如果存在的话
        news_list = news.get("news_list", [])
        if not news_list:
            # 从 key_points 构造伪 news_list
            news_list = [
                {"title": p, "date": "", "source": "AI分析", "summary": p, "sentiment": news.get("新闻情绪", "中性")}
                for p in key_points
            ]
        result_news = {
            "report": news.get("report", ""),
            "key_points": key_points,
            "新闻情绪": news.get("新闻情绪", "中性"),
            "news_list": news_list,
            "platforms": [],
            "analysis": [news.get("report", "")],
        }
    else:
        result_news = dict(news)
        if "sentiment" not in result_news:
            result_news["sentiment"] = result_news.get("新闻情绪", "中性")

    # social_analyst
    social = pa.get("social_analyst", {})
    if "report" in social:
        result_social = {
            "report": social.get("report", ""),
            "key_points": social.get("key_points", []),
            "sentiment_score": social.get("sentiment_score", 0.5),
            "情绪趋势": social.get("情绪趋势", "稳定"),
            "舆情总结": social.get("舆情总结", ""),
            "platforms": [{"name": "综合舆情", "heat": social.get("sentiment_score", 0.5), "sentiment": social.get("情绪趋势", "稳定")}],
            "analysis": [social.get("report", "")],
        }
    else:
        result_social = social

    # v2 中还有 bull_analyst 和 bear_analyst
    # 从 investment_debate 中提取
    debate = data.get("investment_debate", {})
    bull_text = debate.get("bull_r1", "") + "\n\n" + debate.get("bull_r2", "")
    bear_text = debate.get("bear_r1", "") + "\n\n" + debate.get("bear_r2", "")

    result_bull = {
        "bull_detail": {
            "core_logic": bull_text[:200] if bull_text.strip() else "数据不足",
            "bull_case": [p.strip() for p in bull_text.split("\n") if p.strip() and len(p.strip()) > 10][:5] or ["待分析"],
        },
        "role": "bull_analyst",
        "analysis": [bull_text[:500]] if bull_text.strip() else ["待分析"],
    }

    result_bear = {
        "bear_detail": {
            "core_logic": bear_text[:200] if bear_text.strip() else "数据不足",
            "bear_case": [p.strip() for p in bear_text.split("\n") if p.strip() and len(p.strip()) > 10][:5] or ["待分析"],
        },
        "role": "bear_analyst",
        "analysis": [bear_text[:500]] if bear_text.strip() else ["待分析"],
    }

    result["parallel_analysis"] = {
        "tech_analyst": result_tech,
        "fundamentals_analyst": result_fund,
        "news_analyst": result_news,
        "social_analyst": result_social,
        "bull_analyst": result_bull,
        "bear_analyst": result_bear,
    }

    # ===== debate 适配 =====
    # v3: investment_debate 有 4 个文本字段
    # v2: debate 有 rounds 数组
    rounds = []
    if debate.get("bull_r1"):
        rounds.append({"round": 1, "bull": debate["bull_r1"], "bear": debate.get("bear_r1", "")})
    if debate.get("bull_r2"):
        rounds.append({"round": 2, "bull": debate["bull_r2"], "bear": debate.get("bear_r2", "")})

    result["debate"] = {
        "rounds": rounds,
        # 也保留原始 字段供新模板使用
        "investment_debate": debate,
    }

    # ===== manager_decision 适配 =====
    manager = data.get("manager_decision", {})
    if "recommendation" in manager and "decision" not in manager:
        manager["decision"] = manager["recommendation"]
    if "rationale" not in manager:
        manager["rationale"] = manager.get("investment_plan", "")
    result["manager_decision"] = manager

    # ===== trading_plan 直接透传 =====
    result["trading_plan"] = data.get("trading_plan", {})

    # ===== risk_debate 适配 =====
    risk = data.get("risk_debate", {})
    # v3: {"aggressive": "文本", "conservative": "文本", "neutral": "文本"}
    # v2: {"aggressive": {"stance":..., "points":[...]}, ...}
    adapted_risk = {}
    for role in ("aggressive", "conservative", "neutral"):
        val = risk.get(role, {})
        if isinstance(val, str):
            # 纯文本 → 转为 v2 结构
            lines = [l.strip() for l in val.split("\n") if l.strip() and len(l.strip()) > 10]
            # 尝试从文本中提取结构化数据
            import re as _re
            pos_match = _re.search(r'(?:建议仓位|仓位)[：:]\s*(\S+)', val)
            ret_match = _re.search(r'(?:目标收益|预期收益)[：:]\s*(\S+)', val)
            sl_match = _re.search(r'(?:止损控制|止损)[：:]\s*(\S+)', val)
            adapted_risk[role] = {
                "stance": lines[0][:100] if lines else "待评估",
                "points": lines[:5] if lines else ["待分析"],
                "full_text": val,
                "position_size": pos_match.group(1) if pos_match else "详见辩论",
                "target_return": ret_match.group(1) if ret_match else "详见辩论",
                "stop_loss": sl_match.group(1) if sl_match else "详见辩论",
            }
        else:
            adapted_risk[role] = val
    # v2 中有 moderate 而非 neutral
    if "neutral" in adapted_risk and "moderate" not in adapted_risk:
        adapted_risk["moderate"] = adapted_risk["neutral"]
    result["risk_debate"] = adapted_risk

    # ===== final_decision 适配 =====
    final = data.get("final_decision", {})
    # 用 rating，v2 用 final_recommendation
    if "rating" in final and "final_recommendation" not in final:
        final["final_recommendation"] = final["rating"]
    if "executive_summary" in final and "risk_assessment" not in final:
        final["risk_assessment"] = {
            "市场风险": "详见投资论文",
            "流动性风险": "详见投资论文",
            "波动性风险": "详见投资论文",
        }
    result["final_decision"] = final

    return result


def main():
    parser = argparse.ArgumentParser(description="Adapt data to v2 format")
    parser.add_argument("--input", help="Input JSON file path")
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    adapted = adapt_v3_to_v2(data)
    json.dump(adapted, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
