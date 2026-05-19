#!/usr/bin/env python3
"""
validate_step.py — Agent LLM 输出验证 + 日志工具

用途：Agent 每次 LLM 调用后，将输出通过 stdin 传入本脚本进行验证。
- exit 0 + stdout JSON → 验证通过，输出清洗后的 JSON
- exit 1 + stderr JSON → 验证失败，输出错误信息和 hint

用法：
  echo '<LLM输出>' | python3 validate_step.py --step bull_analyst
  echo '<LLM输出>' | python3 validate_step.py --step manager --stock-code PDD --attempt 2

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

# 重试次数上限（供 SKILL.md 参考，脚本本身不执行重试）
RETRY_LIMITS = {
    "parse_input": 3,
    "bull_analyst": 3,
    "bear_analyst": 3,
    "manager": 3,
    "trader": 3,
    "tech_analyst": 2,
    "fundamentals_analyst": 2,
    "news_analyst": 2,
    "social_analyst": 2,
    "debate": 2,
    "risk_debate": 2,
    "risk_manager": 3,
}

# 各步骤必填字段定义（支持嵌套字段用 . 分隔）
# 注意：部分字段有条件必填，见 validate_fields() 函数中的条件逻辑
REQUIRED_FIELDS = {
    "parse_input": ["stock_code", "stock_name"],
    "bull_analyst": ["bull_detail.core_logic", "bull_detail.bull_case"],
    "bear_analyst": ["bear_detail.core_logic", "bear_detail.bear_case"],
    "tech_analyst": ["technical_analysis"],
    "fundamentals_analyst": ["fundamentals_analysis"],
    "news_analyst": ["news_list"],
    "social_analyst": ["sentiment_score"],
    "debate": ["rounds"],
    "manager": ["recommendation", "rationale"],  # 5-tier: Buy/Overweight/Hold/Underweight/Sell,
    "trader": ["decision", "position_size"],  # buy_price/target_price/stop_loss 由条件逻辑处理
    "risk_debate": ["aggressive", "neutral", "conservative"],  # 3派: aggressive/neutral/conservative,
    "risk_manager": ["rating", "risk_level", "investment_horizon", "executive_summary", "investment_thesis"],  # 5-tier rating,
}

# 各步骤的字段提示（用于重试时附加到 prompt）
FIELD_HINTS = {
    "parse_input": '输出必须包含 stock_code（股票代码）和 stock_name（股票名称）字符串字段，以及可选的 current_price、technical_indicators、fundamentals 等',
    "bull_analyst": '输出必须包含 bull_detail 对象，其中 core_logic 为字符串，bull_case 为非空数组',
    "bear_analyst": '输出必须包含 bear_detail 对象，其中 core_logic 为字符串，bear_case 为非空数组',
    "tech_analyst": '输出必须包含 technical_analysis 对象',
    "fundamentals_analyst": '输出必须包含 fundamentals_analysis 对象',
    "news_analyst": '输出必须包含 news_list 数组',
    "social_analyst": '输出必须包含 sentiment_score 数字字段',
    "debate": '输出必须包含 rounds 数组',
    "manager": '输出必须包含 recommendation（买入/增持/持有/减持/卖出）和 rationale 字段。请使用5档评级体系',
    "trader": "输出必须包含 decision（买入/持有/观望）和 position_size 字符串字段。buy_price/target_price/stop_loss 仅在 decision=买入 时必填（数字类型）；持有/观望时允许为 null，但必须提供 reference_price、reference_target、reference_stop 作为参考价格区间",
    "risk_debate": '输出必须包含 aggressive、neutral、conservative 三个对象',
    "risk_manager": '输出必须包含 rating（Buy/Overweight/Hold/Underweight/Sell）、risk_level（低/中/高）、investment_horizon、executive_summary、investment_thesis 字段。使用5档评级体系',
}

# 各步骤的默认值（Agent 全部重试失败后使用）
DEFAULT_VALUES = {
    "parse_input": {
        "stock_code": "UNKNOWN",
        "stock_name": "未知",
        "current_price": None,
        "change_pct": None,
        "volume": None,
        "turnover": None,
        "technical_indicators": {
            "MA5": None, "MA10": None, "MA20": None, "MA60": None,
            "RSI": None, "MACD": None, "KDJ": None,
            "BOLL_upper": None, "BOLL_mid": None, "BOLL_lower": None,
        },
        "fundamentals": {
            "PE": None, "PB": None, "ROE": None,
            "market_cap": None, "revenue": None, "net_profit": None,
        },
        "k_line_pattern": None,
        "other_info": None,
        "_parse_failed": True,
    },
    "bull_analyst": {
        "role": "bull_analyst",
        "analysis": ["LLM 调用失败，使用默认分析"],
        "bull_detail": {
            "core_logic": "LLM 调用失败",
            "bull_case": ["LLM 调用失败，使用默认分析"],
            "risk_alert": "LLM 调用失败",
            "confidenceindex": 0.5,
        },
    },
    "bear_analyst": {
        "role": "bear_analyst",
        "analysis": ["LLM 调用失败，使用默认分析"],
        "bear_detail": {
            "core_logic": "LLM 调用失败",
            "bear_case": ["LLM 调用失败，使用默认分析"],
            "valuationrisk": "LLM 调用失败",
            "downside_risk": "LLM 调用失败",
            "technical_alert": "LLM 调用失败",
            "fundamental_concerns": "LLM 调用失败",
            "risk_events": "LLM 调用失败",
            "confidenceindex": 0.5,
        },
    },
    "tech_analyst": {
        "role": "tech_analyst",
        "analysis": ["LLM 调用失败，使用默认分析"],
        "indicators": {"MA5": "N/A", "RSI": "N/A", "MACD": "N/A"},
        "technical_analysis": {"趋势判断": {}, "关键指标": {}, "技术信号总结": "待分析"},
    },
    "fundamentals_analyst": {
        "role": "fundamentals_analyst",
        "analysis": ["LLM 调用失败，使用默认分析"],
        "metrics": {"PE": "N/A", "PB": "N/A"},
        "fundamentals_analysis": {"估值分析": {}, "盈利能力": {}, "成长性": {}, "财务健康": {}, "综合评价": "待分析"},
    },
    "news_analyst": {
        "role": "news_analyst",
        "analysis": ["LLM 调用失败，使用默认分析"],
        "news_list": [],
        "news_count": 0,
        "sentiment": "中性",
    },
    "social_analyst": {
        "role": "social_analyst",
        "analysis": ["LLM 调用失败，使用默认分析"],
        "sentiment_score": 0.5,
        "platforms": [],
    },
    "debate": {
        "rounds": [{"round": 1, "bull_points": ["待辩论"], "bear_points": ["待辩论"]}],
    },
    "manager": {
        "recommendation": "持有",
        "rationale": "多空力量均衡，建议持有观望",
        "strategic_actions": "建议观望，等待方向明确",
        "_decision_failed": True,
    },
    "trader": {
        "recommendation": "持有",
        "buy_price": None,
        "target_price": None,
        "stop_loss": None,
        "position_size": "10%-15%",
        "entry_criteria": "待制定",
        "exit_criteria": "待制定",
        "_trader_failed": True,
    },
    "risk_debate": {
        "aggressive": {"position": "激进派", "position_size": "25%-40%", "target_return": "20%+", "stop_loss": "-10%"},
        "neutral": {"position": "中性派", "position_size": "15%-20%", "target_return": "10%-15%", "stop_loss": "-7%"},
        "conservative": {"position": "保守派", "position_size": "5%-10%", "target_return": "5%-8%", "stop_loss": "-5%"},
    },
    "risk_manager": {
        "rating": "Hold",
        "risk_level": "中",
        "investment_horizon": "中期(1-6个月)",
        "executive_summary": "多空力量均衡，建议观望等待方向明确",
        "investment_thesis": "基于辩论结果，多空双方论点势均力敌，建议保持中性立场",
        "price_target": None,
        "time_horizon": "3-6个月",
        "_risk_assessment_failed": True,
        "risk_assessment": {"市场风险": "中等", "流动性风险": "低", "波动性风险": "中等"},
        "suitable_investors": ["稳健型"],
        "monitoring_points": ["季度财报发布", "行业政策变化", "技术面破位情况"],
    },
}


# ============================================================
# JSON 清洗与解析
# ============================================================

def fix_json(text: str) -> str:
    """清洗 LLM 输出中常见的 JSON 格式问题"""
    if not text:
        return text

    # 移除 markdown 代码块标记
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # 移除 markdown 标题行
    text = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)

    # 移除行内 markdown 格式
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)

    # 移除尾随逗号
    text = re.sub(r',(\s*[\]\}])', r'\1', text)

    # 移除控制字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    return text.strip()


def extract_json(text: str) -> Optional[Dict]:
    """从文本中提取并解析 JSON 对象"""
    # 先尝试直接解析
    cleaned = fix_json(text)

    # 尝试匹配最外层 {...}
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if not json_match:
        return None

    json_str = json_match.group()

    # 多轮尝试解析
    for attempt in range(3):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            if attempt == 0:
                # 第一次失败：尝试修复单引号
                json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
            elif attempt == 1:
                # 第二次失败：更激进的清洗
                json_str = re.sub(r',(\s*[\]\}])', r'\1', json_str)
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
            # 第三次失败就放弃

    return None


# ============================================================
# 字段验证
# ============================================================

def validate_fields(step: str, data: Dict) -> Tuple[bool, Optional[str]]:
    """
    验证必填字段。
    返回 (is_valid, missing_field_or_None)

    特殊条件逻辑：
    - trader 步骤：buy_price/target_price/stop_loss 仅在 decision="买入" 时必填
    """
    required = REQUIRED_FIELDS.get(step, [])

    for field in required:
        if field == "trader":
            # trader 步骤的条件必填逻辑
            decision = data.get("decision", "")
            if decision == "买入":
                for pf in ["buy_price", "target_price", "stop_loss"]:
                    v = data.get(pf)
                    if v is None or v == "":
                        return False, pf
                # 买入时 also validate position_size
                ps = data.get("position_size", "")
                if not ps or ps == "":
                    return False, "position_size"
            else:
                # 持有/观望：只要求 decision 和 position_size（非null）
                if not data.get("position_size") or data.get("position_size") == "":
                    return False, "position_size"
                # buy_price/target_price/stop_loss 允许为 null（但 reference_* 应有值）
        elif "." in field:
            # 嵌套字段
            parts = field.split(".")
            value = data
            for part in parts:
                if not isinstance(value, dict) or part not in value:
                    return False, field
                value = value[part]
            if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
                return False, field
        else:
            if field not in data or data[field] is None or data[field] == "":
                return False, field

    return True, None


# ============================================================
# 日志
# ============================================================

class StepLogger:
    """分析步骤日志记录器"""

    def __init__(self, stock_code: str = "UNKNOWN"):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.stock_code = stock_code
        now = datetime.now()
        self.log_file = LOG_DIR / f"{stock_code}_{now.strftime('%Y%m%d_%H%M%S')}.log"
        # 使用追加模式，同一次分析的多步共享一个日志文件
        # 通过环境变量传递日志文件路径，保证同一次分析写入同一文件
        env_log = os.environ.get("TRADINGAGENTS_LOG_FILE")
        if env_log:
            self.log_file = Path(env_log)

        # 更新 latest 软链接
        latest = LOG_DIR / "latest.log"
        try:
            if latest.is_symlink() or latest.exists():
                latest.unlink()
            latest.symlink_to(self.log_file.name)
        except OSError:
            pass  # 软链接失败不影响功能

    def log(
        self,
        step: str,
        attempt: int,
        success: bool,
        input_length: int,
        output: Optional[str] = None,
        error: Optional[str] = None,
        raw_first_500: Optional[str] = None,
    ):
        """写入一条日志"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "OK" if success else "FAIL"

        lines = [
            f"[{now}] [{step}] [attempt={attempt}] [{status}]",
            f"  Input length: {input_length} chars",
        ]

        if success and output:
            # 截断过长的输出
            output_preview = output[:500] + ("..." if len(output) > 500 else "")
            lines.append(f"  Output: {output_preview}")
        elif not success:
            if error:
                lines.append(f"  Error: {error}")
            if raw_first_500:
                lines.append(f"  Raw output (first 500 chars): {raw_first_500}")

        lines.append("")  # 空行分隔

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


# ============================================================
# 主入口
# ============================================================

def get_default_value(step: str) -> Dict:
    """获取步骤的默认值"""
    return DEFAULT_VALUES.get(step, {"_failed": True, "error": f"No default for {step}"})


def main():
    parser = argparse.ArgumentParser(
        description="Validate LLM output for a specific analysis step"
    )
    parser.add_argument(
        "--step",
        required=True,
        choices=list(REQUIRED_FIELDS.keys()),
        help="Analysis step name",
    )
    parser.add_argument(
        "--stock-code",
        default="UNKNOWN",
        help="Stock code for log file naming",
    )
    parser.add_argument(
        "--attempt",
        type=int,
        default=1,
        help="Current retry attempt number",
    )
    parser.add_argument(
        "--default",
        action="store_true",
        help="Output default value for the step (skip validation)",
    )
    args = parser.parse_args()

    # 如果请求默认值，直接输出
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

    # 验证通过
    output_str = json.dumps(data, ensure_ascii=False, indent=2)

    logger.log(
        step=args.step,
        attempt=args.attempt,
        success=True,
        input_length=len(raw_input),
        output=output_str,
    )

    # stdout 输出清洗后的 JSON
    sys.stdout.write(output_str)
    sys.stdout.write("\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
