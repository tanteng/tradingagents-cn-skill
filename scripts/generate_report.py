#!/usr/bin/env python3
"""
generate_report.py - PDF 报告生成入口

唯一入口：从 report.json 文件读取完整数据生成 PDF。

用法：
  python3 generate_report.py --input results/NET_report.json
  python3 generate_report.py --input results/NET_report.json --output-dir ./reports
"""
import json
import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Generate PDF report from report.json")
    parser.add_argument("--input", required=True, help="Path to report.json")
    parser.add_argument("--output-dir", default=str(Path(__file__).parent / "reports"))
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    from pdf_generator import ReportGenerator
    generator = ReportGenerator()
    pdf_path = generator.generate(data, output_dir=args.output_dir)
    print(pdf_path)


if __name__ == "__main__":
    main()
