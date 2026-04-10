#!/usr/bin/env python3
"""
CLI entry for PDF report generation.

Usage:
  python3 generate_report.py --input analysis.json
  echo '{"stock_code":"PDD",...}' | python3 generate_report.py --stdin
"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pdf_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate stock analysis PDF report from JSON data"
    )
    parser.add_argument("--input", help="Path to JSON file with analysis data")
    parser.add_argument(
        "--stdin", action="store_true", help="Read JSON from stdin"
    )
    parser.add_argument(
        "--output-dir", help="Custom output directory for PDF"
    )
    args = parser.parse_args()

    if args.stdin:
        data = json.load(sys.stdin)
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
    else:
        parser.print_help()
        sys.exit(1)

    generator = ReportGenerator()
    pdf_path = generator.generate(data, output_dir=args.output_dir)
    print(pdf_path)


if __name__ == "__main__":
    main()
