# analysis_result JSON 数据格式

`generate_report.py` 接收的 JSON 数据结构。Agent 完成 Step 1-6 后，将所有结果组装为此格式。

## 顶层结构

```json
{
  "stock_code": "PDD",
  "stock_name": "拼多多",
  "current_price": 99.54,
  "timestamp": "2026-04-09T22:00:00",
  "final_decision": { ... },
  "trading_plan": { ... },
  "manager_decision": { ... },
  "risk_debate": { ... },
  "parallel_analysis": { ... },
  "debate": { ... }
}
```

## final_decision（风险经理最终决策）

```json
{
  "final_recommendation": "买入/卖出/持有",
  "risk_level": "低/中/高",
  "investment_horizon": "短期/中期/长期",
  "risk_assessment": {
    "市场风险": "描述",
    "流动性风险": "描述",
    "波动性风险": "描述"
  },
  "suitable_investors": ["稳健型", "激进型"],
  "monitoring_points": ["关注点1", "关注点2"]
}
```

## trading_plan（交易计划）

```json
{
  "buy_price": 97.55,
  "target_price": 112.18,
  "stop_loss": 89.75,
  "position_size": "15%-20%",
  "investment_horizon": "6-12个月"
}
```

## manager_decision（研究经理决策）

```json
{
  "decision": "买入/卖出/持有",
  "rationale": "核心逻辑描述"
}
```

## risk_debate（三方风险辩论）

```json
{
  "aggressive": {
    "position": "激进派",
    "position_size": "30%-40%",
    "target_return": "25%+",
    "stop_loss": "-12%"
  },
  "neutral": {
    "position": "中性派",
    "position_size": "15%-20%",
    "target_return": "10%-15%",
    "stop_loss": "-8%"
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
