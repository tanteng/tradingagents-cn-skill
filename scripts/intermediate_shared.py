#!/usr/bin/env python3
"""
中间层文件读写器
所有子 Agent 把结果写入同一个 JSON 文件，各写各的字段，互不覆盖。

Usage:
  python3 intermediate_shared.py --init --stock-code PDD --stock-name 拼多多
  python3 intermediate_shared.py --write --step 多头分析 --data '{"core_logic": "...", "bull_case": [...]}'
  python3 intermediate_shared.py --read
  python3 intermediate_shared.py --status
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
INTERMEDIATE_DIR = SCRIPT_DIR / "intermediate"

# 从 step_schema.json 加载映射
SCHEMA_FILE = SCRIPT_DIR.parent / "references" / "step_schema.json"

def _load_schema() -> dict:
    try:
        with open(SCHEMA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

_SCHEMA = _load_schema()
step_mappings = _SCHEMA.get("step_mappings", {})

# 英文步骤名 → 中文键名（用于 status 字段和结果 JSON 路径）
STEP_KEYS = {
    info["en"]: cn
    for cn, info in step_mappings.items()
}

# 反向映射（中文键名 → 英文步骤名）
KEY_TO_STEP = {v: k for k, v in STEP_KEYS.items()}

# 中文键名 → 结果 JSON 路径
STEP_RESULT_PATH = {
    "stock_data": "结果.股票数据",
    "news_data": "news_data",
    "bull_analyst": "结果.多头分析",
    "bear_analyst": "结果.空头分析",
    "tech_analyst": "结果.技术分析",
    "fundamentals_analyst": "结果.基本面分析",
    "news_analyst": "结果.新闻分析",
    "social_analyst": "结果.社交媒体分析",
    "debate": "结果.辩论过程",
    "manager": "结果.研究经理决策",
    "trader": "结果.交易计划",
    "risk_debate": "结果.风险辩论",
    "risk_manager": "结果.风险经理决策",
}


def get_json_path(stock_code: str) -> Path:
    """获取最新的该股票 JSON 文件路径"""
    files = sorted(INTERMEDIATE_DIR.glob(f"{stock_code}_*.json"))
    if not files:
        raise FileNotFoundError(f"未找到股票 {stock_code} 的中间文件，请先执行 --init")
    return files[-1]


def init_file(stock_code: str, stock_name: str = "") -> Path:
    """初始化一个新的中间文件"""
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{stock_code}_{timestamp}.json"
    json_path = INTERMEDIATE_DIR / filename

    now_iso = datetime.now().isoformat(timespec="seconds")

    # 初始化结构
    data = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "current_price": None,
        "timestamp": now_iso,
        "news_data": [],
        "status": {v: "pending" for v in STEP_KEYS.values()},
        "结果": {},
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return json_path


def write_field(json_path: Path, step_key: str, step_data: dict) -> Path:
    """
    原子写入：将 step_data 写入 json_path 的对应字段。
    step_key 可以是英文步骤名（如 "bull_analyst"）或中文键名（如 "多头分析"）。

    只修改两个地方：
    - 结果.<中文键名> = step_data
    - status.<中文键名> = "done"

    不碰其他任何字段。
    """
    # 解析 step_key
    if step_key in STEP_KEYS:
        # 英文步骤名 → 中文键名
        chinese_key = STEP_KEYS[step_key]
    elif step_key in KEY_TO_STEP:
        chinese_key = step_key
    else:
        chinese_key = step_key  # 假设直接是中文键名

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 写入结果
    data["结果"][chinese_key] = step_data

    # 更新状态
    data["status"][chinese_key] = "done"

    # 原子写回
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return json_path


def read_file(json_path: Path) -> dict:
    """读取整个中间文件"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_status(json_path: Path) -> dict:
    """获取所有步骤的状态"""
    data = read_file(json_path)
    return data.get("status", {})


def main():
    parser = argparse.ArgumentParser(description="中间层文件读写工具")
    parser.add_argument("--stock-code", help="股票代码")
    parser.add_argument("--stock-name", default="", help="股票名称")
    parser.add_argument("--init", action="store_true", help="初始化新文件")
    parser.add_argument("--write", action="store_true", help="写入字段")
    parser.add_argument("--step", help="步骤名（英文或中文）")
    parser.add_argument("--data", help="要写入的 JSON 数据（字符串或 @文件路径）")
    parser.add_argument("--read", action="store_true", help="读取整个文件")
    parser.add_argument("--status", action="store_true", help="查看所有步骤状态")
    parser.add_argument("--path", help="直接指定 JSON 文件路径（省略查找）")
    args = parser.parse_args()

    # 处理 --data 参数（支持 @file 语法）
    data_str = None
    if args.data:
        if args.data.startswith("@"):
            with open(args.data[1:], encoding="utf-8") as f:
                data_str = f.read()
        else:
            data_str = args.data

    # 解析 JSON 数据
    step_data = None
    if data_str:
        step_data = json.loads(data_str)

    # 获取 json_path（--init 不需要，所以先检查 init）
    json_path = None
    if args.path:
        json_path = Path(args.path)
    elif args.stock_code and not args.init:
        json_path = get_json_path(args.stock_code)

    # 执行操作
    if args.init:
        if not args.stock_code:
            parser.print_help()
            sys.exit(1)
        path = init_file(args.stock_code, args.stock_name)
        print(f"初始化完成: {path}")
        return

    if args.write:
        if not json_path or not args.step or step_data is None:
            parser.print_help()
            sys.exit(1)
        path = write_field(json_path, args.step, step_data)
        print(f"写入完成: {path} → 结果.{STEP_KEYS.get(args.step, args.step)}")
        return

    if args.read:
        if not json_path:
            parser.print_help()
            sys.exit(1)
        data = read_file(json_path)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if args.status:
        if not json_path:
            parser.print_help()
            sys.exit(1)
        status = get_status(json_path)
        for k, v in status.items():
            print(f"  {k}: {v}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()