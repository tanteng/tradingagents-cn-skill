#!/usr/bin/env python3
"""
generate_report.py - PDF 报告生成入口

唯一的调用方式：
  echo '<完整JSON>' | python3 generate_report.py

stdin 传入完整的大 JSON（格式见 data_schema.md），输出 PDF 文件路径。
"""
import json
import sys
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description="Generate PDF report from stdin JSON")
    parser.add_argument("--output-dir", default=str(SCRIPT_DIR / "reports"))
    args = parser.parse_args()

    # 唯一入口：从 stdin 读取完整 JSON
    raw = sys.stdin.read().strip()
    if not raw:
        print("Error: no input data from stdin", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # 基本字段验证
    required = ["stock_code", "parallel_analysis", "investment_debate", "final_decision"]
    missing = [f for f in required if f not in data]
    if missing:
        print(f"Error: missing required fields: {missing}", file=sys.stderr)
        sys.exit(1)

    # 生成 PDF
    from pdf_generator import ReportGenerator
    generator = ReportGenerator()
    pdf_path = generator.generate(data, output_dir=args.output_dir)
    print(pdf_path)


if __name__ == "__main__":
    main()
