#!/usr/bin/env python3
"""
assemble_report.py - 从分散的 step 结果文件组装完整的 full_report.json

Agent 在执行过程中会将每步结果保存为独立 JSON 文件。
本脚本将它们组装为 generate_report.py 期望的完整格式。

用法：
  python3 assemble_report.py --results-dir ./results --stock-code 002594 --stock-name "比亚迪" --price 101.67
  python3 assemble_report.py --stdin  (从 stdin 读取元信息 JSON)
"""
import json
import sys
import argparse
import glob
import os
from datetime import datetime
from pathlib import Path


def find_latest_file(results_dir, patterns):
    """按模式查找最新的文件"""
    for pattern in patterns:
        files = sorted(glob.glob(os.path.join(results_dir, pattern)), key=os.path.getmtime, reverse=True)
        if files:
            return files[0]
    return None


def load_json(filepath):
    """安全加载 JSON 文件"""
    if not filepath or not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def assemble(results_dir, stock_code="UNKNOWN", stock_name="未知", current_price=None):
    """从 results 目录组装完整的报告数据"""

    # 查找各步骤的结果文件（支持多种命名模式）
    analysts = load_json(find_latest_file(results_dir, [
        "step3_analysts.json",
        f"{stock_code}_analysts.json",
        f"{stock_code}_step3*.json",
    ]))

    debate = load_json(find_latest_file(results_dir, [
        "steps45_debate.json",
        f"{stock_code}_debate.json",
        f"{stock_code}_steps45*.json",
    ]))

    manager = load_json(find_latest_file(results_dir, [
        "step6_manager.json",
        f"{stock_code}_manager*.json",
    ]))

    trader = load_json(find_latest_file(results_dir, [
        "step7_trader.json",
        f"{stock_code}_trading_plan.json",
        f"{stock_code}_trader*.json",
    ]))

    risk = load_json(find_latest_file(results_dir, [
        "step8_risk.json",
        f"{stock_code}_risk_debate.json",
        f"{stock_code}_risk*.json",
    ]))

    final = load_json(find_latest_file(results_dir, [
        "step9_pm.json",
        f"{stock_code}_final_decision.json",
        f"{stock_code}_pm*.json",
    ]))

    news = load_json(find_latest_file(results_dir, [
        f"{stock_code}_news_data.json",
        "news_data.json",
    ]))

    # 组装完整 JSON
    report = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "current_price": current_price,
        "timestamp": datetime.now().isoformat(),

        "news_data": news if news else {"news_list": []},

        "parallel_analysis": {
            "tech_analyst": analysts.get("tech_analyst", {}),
            "fundamentals_analyst": analysts.get("fundamentals_analyst", {}),
            "news_analyst": analysts.get("news_analyst", {}),
            "social_analyst": analysts.get("social_analyst", {}),
        },

        "investment_debate": {
            "bull_r1": debate.get("bull_r1", ""),
            "bear_r1": debate.get("bear_r1", ""),
            "bull_r2": debate.get("bull_r2", ""),
            "bear_r2": debate.get("bear_r2", ""),
        },

        "manager_decision": manager,
        "trading_plan": trader,

        "risk_debate": {
            "aggressive": risk.get("aggressive", ""),
            "conservative": risk.get("conservative", ""),
            "neutral": risk.get("neutral", risk.get("moderate", "")),
        },

        "final_decision": final,
    }

    # 确保 news_list 注入到 news_analyst
    if report["news_data"].get("news_list") and not report["parallel_analysis"]["news_analyst"].get("news_list"):
        report["parallel_analysis"]["news_analyst"]["news_list"] = report["news_data"]["news_list"]

    return report


def main():
    parser = argparse.ArgumentParser(description="Assemble full report from step result files")
    parser.add_argument("--results-dir", default=str(Path(__file__).parent / "results"))
    parser.add_argument("--stock-code", default="UNKNOWN")
    parser.add_argument("--stock-name", default="未知")
    parser.add_argument("--price", type=float, default=None)
    parser.add_argument("--stdin", action="store_true", help="Read meta info from stdin")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    if args.stdin:
        meta = json.load(sys.stdin)
        args.stock_code = meta.get("stock_code", args.stock_code)
        args.stock_name = meta.get("stock_name", args.stock_name)
        args.price = meta.get("current_price", args.price)
        if meta.get("results_dir"):
            args.results_dir = meta["results_dir"]

    report = assemble(args.results_dir, args.stock_code, args.stock_name, args.price)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Assembled: {args.output}", file=sys.stderr)
    else:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
