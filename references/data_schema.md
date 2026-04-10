# analysis_result JSON 数据格式 

`generate_report.py` 接收的 JSON 数据结构。Agent 完成 17 步分析后，将所有结果组装为此格式。

## 顶层结构

```json
{
  "stock_code": "PDD",
  "stock_name": "拼多多",
  "current_price": 99.54,
  "timestamp": "2026-04-09T22:00:00",
  "parallel_analysis": { ... },
  "investment_debate": { ... },
  "manager_decision": { ... },
  "trading_plan": { ... },
  "risk_debate": { ... },
  "final_decision": { ... }
}
```

## parallel_analysis（四位分析师报告）

```json
{
  "tech_analyst": {
    "report": "完整的技术分析报告（中文长文本）",
    "key_points": ["要点1", "要点2", ...],
    "indicators": {
      "趋势方向": "上升/下降/震荡",
      "支撑位": "数值",
      "压力位": "数值",
      "RSI": "数值或N/A",
      "MACD信号": "金叉/死叉/中性",
      "均线排列": "多头排列/空头排列/交织",
      "成交量配合": "放量/缩量/正常"
    },
    "技术信号总结": "总体判断",
    "操作建议": {"支撑位": "数值", "压力位": "数值", "止损位": "数值"}
  },
  "fundamentals_analyst": {
    "report": "完整的基本面分析报告（中文长文本）",
    "key_points": ["要点1", "要点2", ...],
    "financials": {"PE": "数值", "PB": "数值", ...},
    "估值评估": "低估/合理/高估",
    "基本面总结": "总体判断"
  },
  "news_analyst": {
    "report": "完整的新闻分析报告（中文长文本）",
    "key_points": ["要点1", "要点2", ...],
    "新闻情绪": "偏多/中性/偏空",
    "关键催化剂": ["催化剂1", ...],
    "风险事件": ["风险1", ...]
  },
  "social_analyst": {
    "report": "完整的情绪分析报告（中文长文本）",
    "key_points": ["要点1", "要点2", ...],
    "sentiment_score": 0.65,
    "情绪趋势": "上升/稳定/下降",
    "舆情总结": "总体判断"
  }
}
```

## investment_debate（多空辩论，2轮）

```json
{
  "bull_r1": "看多研究员第一轮论证（中文长文本）",
  "bear_r1": "看空研究员第一轮论证（中文长文本）",
  "bull_r2": "看多研究员第二轮回应（中文长文本）",
  "bear_r2": "看空研究员第二轮回应（中文长文本）"
}
```

## manager_decision（研究管理者裁决）

```json
{
  "recommendation": "买入/卖出/持有",
  "rationale": "决策理由",
  "investment_plan": "详细投资计划",
  "bull_strength": "看多方最有力论点总结",
  "bear_strength": "看空方最有力论点总结",
  "key_risks": ["风险1", "风险2", "风险3"]
}
```

## trading_plan（交易员计划）

```json
{
  "decision": "买入/卖出/观望",
  "buy_price": 数字或null,
  "target_price": 数字或null,
  "stop_loss": 数字或null,
  "reference_price": 数字,
  "reference_target": 数字,
  "reference_stop": 数字,
  "position_size": "15%-20%",
  "entry_criteria": "入场条件描述",
  "exit_criteria": "出场条件描述"
}
```

## risk_debate（风控三方辩论）

```json
{
  "aggressive": "激进型分析师辩论发言（中文长文本）",
  "conservative": "保守型分析师辩论发言（中文长文本）",
  "neutral": "中立型分析师辩论发言（中文长文本）"
}
```

## final_decision（投资组合经理最终决策）

```json
{
  "rating": "买入/增持/持有/减持/卖出",
  "executive_summary": "执行摘要（入场策略、仓位建议、风险水平、时间周期）",
  "investment_thesis": "投资论文（详细推理过程）",
  "risk_level": "低/中/高",
  "investment_horizon": "短期/中期/长期",
  "risk_assessment": {
    "市场风险": "评估描述",
    "流动性风险": "评估描述",
    "波动性风险": "评估描述"
  },
  "suitable_investors": ["投资者类型1", "投资者类型2"],
  "monitoring_points": ["监控要点1", "监控要点2", "监控要点3"]
}
```
