#!/usr/bin/env python3
"""
CLI entry for PDF report generation.

Usage:
  python3 generate_report.py --from-file analysis.json
  python3 generate_report.py --from-file /path/to/PDD_20260520_092100.json
  echo '{"stock_code": "PDD", ...}' | python3 generate_report.py --stdin
"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pdf_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate stock analysis PDF report"
    )
    parser.add_argument(
        "--from-file",
        help="Path to shared intermediate JSON file"
    )
    parser.add_argument(
        "--input",
        help="Path to JSON file (legacy, same as --from-file)"
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read JSON from stdin"
    )
    parser.add_argument(
        "--output-dir",
        help="Custom output directory for PDF"
    )
    args = parser.parse_args()

    if args.stdin:
        data = json.load(sys.stdin)
    elif args.from_file:
        with open(args.from_file, encoding="utf-8") as f:
            data = json.load(f)
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
    else:
        parser.print_help()
        sys.exit(1)

    generator = ReportGenerator()
    # Normalize risk_debate: neutral <-> moderate (两种命名都接受)
    if "结果" in data:
        risk = data.get("结果", {}).get("风险辩论", {})
        if risk and "moderate" in risk and "neutral" not in risk:
            risk["neutral"] = risk.pop("moderate")
        # Normalize decision copying from manager → trader
        manager_decision = data.get("结果", {}).get("研究经理决策", {})
        trading_plan = data.get("结果", {}).get("交易计划", {})
        if manager_decision and "decision" in manager_decision and not trading_plan.get("decision"):
            trading_plan["decision"] = manager_decision["decision"]

    pdf_path = generator.generate(data, output_dir=args.output_dir)
    print(pdf_path)


if __name__ == "__main__":
    main()
