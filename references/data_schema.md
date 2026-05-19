# analysis_result JSON 数据格式

`generate_report.py` 接收的 JSON 数据结构。Agent 完成 Step 1-11 后，将所有结果组装为此格式。

## 顶层结构

```json
{
  "stock_code": "PDD",
  "stock_name": "拼多多",
  "current_price": 99.54,
  "timestamp": "2026-04-09T22:00:00",
  "parallel_analysis": { ... },
  "debate": { ... },
  "manager_decision": { ... },
  "trading_plan": { ... },
  "risk_debate": { ... },
  "final_decision": { ... }
}
```

## manager_decision（研究经理决策）

对应原始项目的 PortfolioDecision。必须包含：
```json
{
  "recommendation": "买入/增持/持有/减持/卖出",
  "rationale": "核心逻辑（1-2句话解释决策理由）",
  "strategic_actions": "交易员的具体执行步骤，包括仓位指导"
}
```

**5档评级体系：**
| 中文评级 | 英文评级 | 含义 |
|---------|---------|------|
| 买入 | Buy | 强烈看多，建议买入 |
| 增持 | Overweight | 看好，建议逐步加仓 |
| 持有 | Hold | 中性观望 |
| 减持 | Underweight | 看空，建议减仓 |
| 卖出 | Sell | 强烈看空，建议清仓 |

## trading_plan（交易计划）

对应原始项目的 TraderProposal。所有价格必须是数字类型：
```json
{
  "decision": "买入",
  "buy_price": 97.55,
  "target_price": 112.18,
  "stop_loss": 89.75,
  "reference_price": 99.54,
  "reference_target": 109.49,
  "reference_stop": 94.56,
  "position_size": "15%-20%",
  "entry_criteria": "价格回调至97.55元附近企稳后入场",
  "exit_criteria": "跌破89.75元止损或达到112.18元目标"
}
```

| 研究经理决策 | trading_plan.decision | 价格字段 | position_size |
|-------------|----------------------|---------|---------------|
| 买入/增持 | 买入/增持 | 必填数字 | "15%-20%" |
| 持有/减持/卖出 | 持有/减持/卖出 | null | "0%" |

## final_decision（风险经理最终决策）

对应原始项目的 PortfolioDecision（带 Rating 字段）。必须包含：
```json
{
  "rating": "Buy/Overweight/Hold/Underweight/Sell",
  "risk_level": "低/中/高",
  "investment_horizon": "短期(1-4周)/中期(1-6个月)/长期(6个月以上)",
  "executive_summary": "简洁的行动计划，2-4句话",
  "investment_thesis": "详细的推理依据，基于辩论中的具体证据",
  "price_target": 数字或null,
  "time_horizon": "如：3-6个月",
  "risk_assessment": {
    "市场风险": "描述",
    "流动性风险": "描述",
    "波动性风险": "描述"
  },
  "suitable_investors": ["激进型", "稳健型", "保守型"],
  "monitoring_points": ["关注点1", "关注点2"]
}
```

## risk_debate（三方风险辩论）

```json
{
  "aggressive": {
    "position": "激进派",
    "position_size": "25%-40%",
    "target_return": "20%+",
    "stop_loss": "-10%"
  },
  "neutral": {
    "position": "中性派",
    "position_size": "15%-20%",
    "target_return": "10%-15%",
    "stop_loss": "-7%"
  },
  "conservative": {
    "position": "保守派",
    "position_size": "5%-10%",
    "target_return": "5%-8%",
    "stop_loss": "-5%"
  }
}
```

## parallel_analysis（6 个分析师结果）

```json
{
  "bull_analyst": {
    "analysis": ["看多论点1", "看多论点2"],
    "bull_detail": {
      "core_logic": "核心逻辑",
      "bull_case": ["论点1", "论点2"],
      "risk_alert": "风险提示",
      "confidenceindex": 0.7
    }
  },
  "bear_analyst": {
    "analysis": ["看空论点1"],
    "bear_detail": {
      "core_logic": "核心逻辑",
      "bear_case": ["论点1", "论点2"],
      "valuationrisk": "估值风险",
      "downside_risk": "下行风险",
      "technical_alert": "技术面警示",
      "fundamental_concerns": "基本面担忧",
      "risk_events": "风险事件",
      "confidenceindex": 0.6
    }
  },
  "tech_analyst": {
    "analysis": ["技术面总结"],
    "indicators": {"MA5": "101", "RSI": "45", "MACD": "金叉"},
    "technical_analysis": { ... }
  },
  "fundamentals_analyst": {
    "analysis": ["基本面总结"],
    "metrics": {"PE": "10.18", "PB": "2.5"},
    "fundamentals_analysis": { ... }
  },
  "news_analyst": {
    "news_list": [
      {"title": "标题", "date": "2026-04-07", "source": "来源", "summary": "摘要", "sentiment": "偏多"}
    ],
    "news_count": 5,
    "sentiment": "偏多/偏空/中性"
  },
  "social_analyst": {
    "sentiment_score": 0.6,
    "platforms": ["雪球", "东方财富"]
  }
}
```

## debate（多空辩论）

```json
{
  "rounds": [
    {
      "round": 1,
      "bull_points": ["多头论点1", "多头论点2"],
      "bear_points": ["空头论点1", "空头论点2"]
    }
  ]
}
```

## news_data 格式

每条新闻必须包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| title | string | 新闻标题 |
| date | string | YYYY-MM-DD 格式 |
| source | string | 媒体来源 |
| summary | string | ≤50字摘要（必填，不能为空） |
| sentiment | string | "偏多" / "偏空" / "中性" |