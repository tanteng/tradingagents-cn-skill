#!/usr/bin/env python3
"""
validate_step.py — Agent LLM 输出验证 + 日志工具 (TradingAgents-CN)

适配 TradingAgents-CN 17 步工作流。

用途：Agent 每次 LLM 调用后，将输出通过 stdin 传入本脚本进行验证。
- exit 0 + stdout JSON → 验证通过，输出清洗后的 JSON
- exit 1 + stderr JSON → 验证失败，输出错误信息和 hint

用法：
  # 初始化 report.json
  python3 validate_step.py --init '{"stock_code":"NET","stock_name":"Cloudflare","current_price":168.94,"news_data":{"news_list":[...]}}' --stock-code NET

  # 验证 + 保存到 report.json
  echo '<LLM输出>' | python3 validate_step.py --step tech --stock-code NET --save

  # 辩论 R2
  echo '<LLM输出>' | python3 validate_step.py --step bull_debate --stock-code NET --round 2 --save

  # 获取默认值
  python3 validate_step.py --step tech --default

日志写入 {script_dir}/logs/ 目录。
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 配置
# ============================================================

SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR / "logs"

# step 名 → report.json 中的字段路径
# validate --save 时，把验证通过的数据写入 report.json 的对应位置
STEP_TO_PATH = {
    "step1b":             None,  # step1b 数据由 --init 初始化
    "tech":               "parallel_analysis.tech_analyst",
    "fundamentals":       "parallel_analysis.fundamentals_analyst",
    "news":               "parallel_analysis.news_analyst",
    "bull_debate":        "investment_debate.bull_r1",  # R1/R2 由 --round 决定
    "bear_debate":        "investment_debate.bear_r1",
    "manager":            "manager_decision",
    "trader":             "trading_plan",
    "risk_aggressive":    "risk_debate.aggressive",
    "risk_conservative":  "risk_debate.conservative",
    "risk_neutral":       "risk_debate.neutral",
    "portfolio_manager":  "final_decision",
}

# 重试次数上限（供 SKILL.md 参考，脚本本身不执行重试）
RETRY_LIMITS = {
    "step1b": 3,
    "tech": 2,
    "fundamentals": 2,
    "news": 2,
    "manager": 3,
    "trader": 3,
    "portfolio_manager": 3,
    "bull_debate": 2,
    "bear_debate": 2,
    "risk_aggressive": 2,
    "risk_conservative": 2,
    "risk_neutral": 2,
}

# 各步骤必填字段定义（支持嵌套字段用 . 分隔）
REQUIRED_FIELDS = {
    "step1b": ["stock_code", "stock_name"],
    "tech": ["report", "key_points"],
    "fundamentals": ["report", "key_points"],
    "news": ["report", "key_points"],
    "manager": ["recommendation", "rationale", "investment_plan"],
    "trader": ["decision"],
    "portfolio_manager": ["rating", "executive_summary", "investment_thesis", "risk_level"],
    "bull_debate": ["debate_text", "core_logic", "bull_case", "confidence"],
    "bear_debate": ["debate_text", "core_logic", "bear_case", "confidence"],
    "risk_aggressive": ["debate_text", "stance", "position_size", "key_points"],
    "risk_conservative": ["debate_text", "stance", "position_size", "key_points"],
    "risk_neutral": ["debate_text", "stance", "position_size", "key_points"],
    # 保留旧步骤名兼容
    "parse_input": ["stock_code", "stock_name"],
    "bull_analyst": ["bull_detail.core_logic", "bull_detail.bull_case"],
    "bear_analyst": ["bear_detail.core_logic", "bear_detail.bear_case"],
    "tech_analyst": ["technical_analysis"],
    "fundamentals_analyst": ["fundamentals_analysis"],
    "news_analyst": ["news_list"],
    "social_analyst": ["sentiment_score"],
    "debate": ["rounds"],
    "risk_debate": ["aggressive", "moderate", "conservative"],
    "risk_manager": ["final_recommendation", "risk_level", "risk_assessment"],
}

# 各步骤的字段提示（用于重试时附加到 prompt）
FIELD_HINTS = {
    "step1b": '输出必须包含 stock_code（股票代码）和 stock_name（股票名称）字符串字段',
    "tech": '输出必须包含 report（500字以上的中文分析报告）和 key_points（要点数组）字段',
    "fundamentals": '输出必须包含 report（500字以上的中文分析报告）和 key_points（要点数组）字段',
    "news": '输出必须包含 report（500字以上的中文分析报告）和 key_points（要点数组）字段',
    "manager": '输出必须包含 recommendation（买入/卖出/持有）、rationale（决策理由）和 investment_plan（投资计划）字段',
    "trader": '输出必须包含 decision（买入/卖出/观望）字段，买入时还需 buy_price、target_price、stop_loss 数字字段',
    "portfolio_manager": '输出必须包含 rating（买入/增持/持有/减持/卖出五级之一）、executive_summary、investment_thesis 和 risk_level 字段',
    "bull_debate": '输出必须是JSON，包含 debate_text（看多论述500字以上）、core_logic（核心逻辑1-2句话）、bull_case（3-5个论点数组）、confidence（0-1浮点数）',
    "bear_debate": '输出必须是JSON，包含 debate_text（看空论述500字以上）、core_logic（核心逻辑1-2句话）、bear_case（3-5个论点数组）、confidence（0-1浮点数）',
    "risk_aggressive": '输出必须是JSON，包含 debate_text（激进派论述）、stance（立场）、position_size（仓位百分比如30%-40%）、key_points（2-4个要点数组）',
    "risk_conservative": '输出必须是JSON，包含 debate_text（保守派论述）、stance（立场）、position_size（仓位百分比如5%-10%）、key_points（2-4个要点数组）',
    "risk_neutral": '输出必须是JSON，包含 debate_text（中立派论述）、stance（立场）、position_size（仓位百分比如15%-20%）、key_points（2-4个要点数组）',
    # 保留旧提示兼容
    "parse_input": '输出必须包含 stock_code（股票代码）和 stock_name（股票名称）字符串字段',
    "bull_analyst": '输出必须包含 bull_detail 对象，其中 core_logic 为字符串，bull_case 为非空数组',
    "bear_analyst": '输出必须包含 bear_detail 对象，其中 core_logic 为字符串，bear_case 为非空数组',
    "tech_analyst": '输出必须包含 technical_analysis 对象',
    "fundamentals_analyst": '输出必须包含 fundamentals_analysis 对象',
    "news_analyst": '输出必须包含 news_list 数组',
    "social_analyst": '输出必须包含 sentiment_score 数字字段',
    "debate": '输出必须包含 rounds 数组',
    "risk_debate": '输出必须包含 aggressive、moderate、conservative 三个对象',
    "risk_manager": '输出必须包含 final_recommendation、risk_level、risk_assessment 字段',
}


# ============================================================
# 日志
# ============================================================

class StepLogger:
    def __init__(self, stock_code: str = "UNKNOWN"):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.stock_code = stock_code
        # 使用环境变量中的日志文件，否则创建默认文件
        self.log_file = os.environ.get("TRADINGAGENTS_LOG_FILE")
        if not self.log_file:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = str(LOG_DIR / f"{stock_code}_{ts}.log")

    def log(self, step: str, attempt: int = 1, success: bool = True,
            input_length: int = 0, output: str = "", error: str = "",
            raw_first_500: str = ""):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "OK" if success else "FAIL"
        entry = {
            "ts": ts,
            "step": step,
            "attempt": attempt,
            "status": status,
            "input_len": input_length,
        }
        if error:
            entry["error"] = error
        if raw_first_500:
            entry["raw_preview"] = raw_first_500

        line = json.dumps(entry, ensure_ascii=False)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


# ============================================================
# JSON 提取
# ============================================================

def extract_json(raw: str) -> Optional[Dict]:
    """尝试从 LLM 输出中提取 JSON 对象。"""
    # 1. 尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. 去掉 markdown 代码块
    patterns = [
        r'```json\s*\n?(.*?)\n?\s*```',
        r'```\s*\n?(.*?)\n?\s*```',
    ]
    for pat in patterns:
        m = re.search(pat, raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                continue

    # 3. 寻找第一个 { 到最后一个 }
    first_brace = raw.find('{')
    last_brace = raw.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(raw[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    return None


# ============================================================
# 字段验证
# ============================================================

def get_nested(data: Dict, path: str) -> Any:
    """通过点分路径获取嵌套字段值。"""
    parts = path.split(".")
    current = data
    for p in parts:
        if isinstance(current, dict) and p in current:
            current = current[p]
        else:
            return None
    return current


def validate_fields(step: str, data: Dict) -> Tuple[bool, Optional[str]]:
    """验证指定步骤的必填字段。返回 (is_valid, missing_field)。"""
    required = REQUIRED_FIELDS.get(step, [])
    for field_path in required:
        val = get_nested(data, field_path)
        if val is None:
            return False, field_path
        if isinstance(val, str) and val.strip() == "":
            return False, field_path
        if isinstance(val, list) and len(val) == 0:
            return False, field_path
    return True, None


# ============================================================
# trader 特殊验证：买入时价格必须是数字
# ============================================================

def validate_trader(data: Dict) -> Tuple[bool, Optional[str]]:
    """交易员输出的特殊验证。"""
    decision = data.get("decision", "")
    if decision in ("买入", "buy", "Buy", "BUY"):
        for field in ("buy_price", "target_price", "stop_loss"):
            val = data.get(field)
            if val is None:
                return False, field
            if isinstance(val, str):
                return False, f"{field}（必须是数字，不能是字符串 '{val}'）"
            if not isinstance(val, (int, float)):
                return False, f"{field}（必须是数字类型）"
    return True, None


# ============================================================
# portfolio_manager 特殊验证：评级必须是五级之一
# ============================================================

VALID_RATINGS = {"买入", "增持", "持有", "减持", "卖出"}

def validate_portfolio_manager(data: Dict) -> Tuple[bool, Optional[str]]:
    """投资组合经理输出的特殊验证。"""
    rating = data.get("rating", "")
    if rating not in VALID_RATINGS:
        return False, f"rating（必须是以下五级之一：{'/'.join(VALID_RATINGS)}，当前值：'{rating}'）"
    return True, None


# ============================================================
# 默认值
# ============================================================

def get_default_value(step: str) -> Dict:
    """返回各步骤的安全默认值。"""
    defaults = {
        "step1b": {
            "stock_code": "UNKNOWN",
            "stock_name": "未知",
            "current_price": None,
            "change_pct": None,
            "volume": None,
            "turnover": None,
            "technical_indicators": {},
            "fundamentals": {},
            "k_line_pattern": None,
            "other_info": None,
        },
        "tech": {
            "report": "技术分析数据不足，无法生成完整报告。",
            "key_points": ["数据不足"],
            "indicators": {},
            "signal_summary": "数据不足",
            "trade_advice": {"support": "N/A", "resistance": "N/A", "stop_loss": "N/A"},
        },
        "fundamentals": {
            "report": "基本面数据不足，无法生成完整报告。",
            "key_points": ["数据不足"],
            "financials": {},
            "valuation_summary": "无法判断",
            "fundamental_rating": "数据不足",
        },
        "news": {
            "report": "新闻数据不足，无法生成完整报告。",
            "key_points": ["数据不足"],
            "sentiment": "中性",
            "catalysts": [],
            "risk_events": [],
        },
        "manager": {
            "recommendation": "持有",
            "rationale": "多空辩论结果不明确，建议暂时持有观望。",
            "investment_plan": "维持现有仓位，等待更多信息再做决策。",
            "bull_strength": "数据不足",
            "bear_strength": "数据不足",
            "key_risks": ["信息不足"],
        },
        "trader": {
            "decision": "观望",
            "buy_price": None,
            "target_price": None,
            "stop_loss": None,
            "reference_price": None,
            "reference_target": None,
            "reference_stop": None,
            "position_size": "0%",
            "entry_criteria": "等待更多信息",
            "exit_criteria": "不适用",
        },
        "portfolio_manager": {
            "rating": "持有",
            "executive_summary": "信息不足，建议暂时持有观望，等待更多数据验证。",
            "investment_thesis": "由于分析数据不足，无法做出强有力的投资判断。建议维持现有仓位。",
            "risk_level": "中",
            "investment_horizon": "待定",
            "risk_assessment": {
                "market_risk": "待评估",
                "liquidity_risk": "待评估",
                "volatility_risk": "待评估",
            },
            "suitable_investors": ["稳健型"],
            "monitoring_points": ["等待更多数据"],
        },
        # 保留旧步骤默认值兼容
        "parse_input": {"stock_code": "UNKNOWN", "stock_name": "未知"},
        "bull_analyst": {"bull_detail": {"core_logic": "数据不足", "bull_case": ["待分析"]}},
        "bear_analyst": {"bear_detail": {"core_logic": "数据不足", "bear_case": ["待分析"]}},
        "tech_analyst": {"technical_analysis": "数据不足"},
        "fundamentals_analyst": {"fundamentals_analysis": "数据不足"},
        "news_analyst": {"news_list": []},
        "social_analyst": {"sentiment_score": 0.5},
        "debate": {"rounds": []},
        "risk_debate": {
            "aggressive": {"stance": "待评估", "points": []},
            "moderate": {"stance": "待评估", "points": []},
            "conservative": {"stance": "待评估", "points": []},
        },
        "risk_manager": {
            "final_recommendation": "持有",
            "risk_level": "中",
            "investment_horizon": "待定",
            "risk_assessment": {"market_risk": "待评估", "liquidity_risk": "待评估", "volatility_risk": "待评估"},
            "suitable_investors": ["稳健型"],
            "monitoring_points": ["等待更多数据"],
        },
    }
    return defaults.get(step, {"error": f"Unknown step: {step}"})


# ============================================================
# 主函数
# ============================================================

def _get_report_path(stock_code):
    """获取 report.json 的路径"""
    results_dir = SCRIPT_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir / f"{stock_code}_report.json"


def _set_nested(d, path, value):
    """按 a.b.c 路径设置嵌套字典的值"""
    keys = path.split(".")
    for k in keys[:-1]:
        if k not in d or not isinstance(d[k], dict):
            d[k] = {}
        d = d[k]
    d[keys[-1]] = value


def init_report(stock_code, stock_name="", current_price=None, news_data=None):
    """初始化 report.json 骨架"""
    report = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "current_price": current_price,
        "timestamp": datetime.now().isoformat(),
        "news_data": news_data or {"news_list": []},
        "parallel_analysis": {
            "tech_analyst": {},
            "fundamentals_analyst": {},
            "news_analyst": {},
        },
        "investment_debate": {
            "bull_r1": {},
            "bear_r1": {},
            "bull_r2": {},
            "bear_r2": {},
        },
        "manager_decision": {},
        "trading_plan": {},
        "risk_debate": {
            "aggressive": {},
            "conservative": {},
            "neutral": {},
        },
        "final_decision": {},
    }
    rp = _get_report_path(stock_code)
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return str(rp)


def _save_to_report(step, stock_code, data, round_num=1):
    """把验证通过的数据写入 report.json 的对应字段"""
    rp = _get_report_path(stock_code)

    # 读取已有 report
    if rp.exists():
        with open(rp, "r", encoding="utf-8") as f:
            report = json.load(f)
    else:
        # 如果没有就初始化
        report = json.loads(json.dumps({
            "stock_code": stock_code, "stock_name": "", "current_price": None,
            "timestamp": datetime.now().isoformat(),
            "news_data": {"news_list": []},
            "parallel_analysis": {"tech_analyst": {}, "fundamentals_analyst": {}, "news_analyst": {}},
            "investment_debate": {"bull_r1": {}, "bear_r1": {}, "bull_r2": {}, "bear_r2": {}},
            "manager_decision": {}, "trading_plan": {},
            "risk_debate": {"aggressive": {}, "conservative": {}, "neutral": {}},
            "final_decision": {},
        }))

    # 确定写入路径
    path = STEP_TO_PATH.get(step)
    if not path:
        return

    # 辩论步骤需要区分 R1/R2
    if step == "bull_debate":
        path = f"investment_debate.bull_r{round_num}"
    elif step == "bear_debate":
        path = f"investment_debate.bear_r{round_num}"

    _set_nested(report, path, data)

    # 写回
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Validate LLM output for a given step")
    parser.add_argument("--step", help="Step name")
    parser.add_argument("--stock-code", default="UNKNOWN", help="Stock code for logging")
    parser.add_argument("--attempt", type=int, default=1, help="Attempt number")
    parser.add_argument("--default", action="store_true", help="Output default value for the step")
    parser.add_argument("--save", action="store_true", help="Save validated result to report.json")
    parser.add_argument("--init", help="Initialize report.json with stock metadata JSON string")
    parser.add_argument("--round", type=int, default=1, choices=[1, 2], help="Debate round number (1 or 2)")
    args = parser.parse_args()

    # 如果请求默认值，直接输出
    # --init: 初始化 report.json
    if args.init:
        try:
            meta = json.loads(args.init)
        except json.JSONDecodeError:
            meta = json.load(sys.stdin)
        rp = init_report(
            stock_code=meta.get("stock_code", args.stock_code or "UNKNOWN"),
            stock_name=meta.get("stock_name", ""),
            current_price=meta.get("current_price"),
            news_data=meta.get("news_data"),
        )
        print(rp)
        sys.exit(0)

    # 非 --init 模式必须提供 --step
    if not args.init and not args.step:
        parser.error("--step is required (unless using --init)")

    if args.default:
        default = get_default_value(args.step)
        json.dump(default, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        sys.exit(0)

    # 读取 stdin
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        error_obj = {
            "error": "empty_input",
            "field": None,
            "step": args.step,
            "hint": "LLM 输出为空，请重新调用",
        }
        json.dump(error_obj, sys.stderr, ensure_ascii=False)
        sys.stderr.write("\n")
        sys.exit(1)

    # 初始化日志
    logger = StepLogger(stock_code=args.stock_code)

    # 尝试提取 JSON
    data = extract_json(raw_input)

    if data is None:
        # JSON 解析失败
        error_msg = "无法从 LLM 输出中提取有效 JSON"
        hint = FIELD_HINTS.get(args.step, "请以纯 JSON 格式返回，不要包含 markdown 代码块")
        error_obj = {
            "error": "json_parse_failed",
            "field": None,
            "step": args.step,
            "hint": f"上次输出无法解析为 JSON。{hint}。请返回纯 JSON，不要用 ```json 代码块包裹。",
        }

        logger.log(
            step=args.step,
            attempt=args.attempt,
            success=False,
            input_length=len(raw_input),
            error=error_msg,
            raw_first_500=raw_input[:500],
        )

        json.dump(error_obj, sys.stderr, ensure_ascii=False)
        sys.stderr.write("\n")
        sys.exit(1)

    # 验证必填字段
    is_valid, missing_field = validate_fields(args.step, data)

    if not is_valid:
        error_msg = f"Missing required field: {missing_field}"
        hint = FIELD_HINTS.get(args.step, f"请确保输出包含 {missing_field} 字段")
        error_obj = {
            "error": "missing_field",
            "field": missing_field,
            "step": args.step,
            "hint": f"上次输出缺少必填字段 {missing_field}。{hint}",
        }

        logger.log(
            step=args.step,
            attempt=args.attempt,
            success=False,
            input_length=len(raw_input),
            error=error_msg,
            raw_first_500=raw_input[:500],
        )

        json.dump(error_obj, sys.stderr, ensure_ascii=False)
        sys.stderr.write("\n")
        sys.exit(1)

    # trader 特殊验证
    if args.step == "trader":
        is_valid, err_field = validate_trader(data)
        if not is_valid:
            error_obj = {
                "error": "invalid_trader_field",
                "field": err_field,
                "step": args.step,
                "hint": f"交易员输出的价格字段有误：{err_field}。买入决策时 buy_price/target_price/stop_loss 必须是具体数字。",
            }
            logger.log(step=args.step, attempt=args.attempt, success=False,
                        input_length=len(raw_input), error=str(err_field))
            json.dump(error_obj, sys.stderr, ensure_ascii=False)
            sys.stderr.write("\n")
            sys.exit(1)

    # portfolio_manager 特殊验证
    if args.step == "portfolio_manager":
        is_valid, err_field = validate_portfolio_manager(data)
        if not is_valid:
            error_obj = {
                "error": "invalid_rating",
                "field": err_field,
                "step": args.step,
                "hint": f"投资组合经理评级无效：{err_field}",
            }
            logger.log(step=args.step, attempt=args.attempt, success=False,
                        input_length=len(raw_input), error=str(err_field))
            json.dump(error_obj, sys.stderr, ensure_ascii=False)
            sys.stderr.write("\n")
            sys.exit(1)

    # 验证通过
    output_str = json.dumps(data, ensure_ascii=False, indent=2)

    logger.log(
        step=args.step,
        attempt=args.attempt,
        success=True,
        input_length=len(raw_input),
        output=output_str,
    )

    # --save: 写入 report.json
    if args.save and args.stock_code:
        _save_to_report(args.step, args.stock_code, data, args.round)

    # stdout 输出清洗后的 JSON
    sys.stdout.write(output_str)
    sys.stdout.write("\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
