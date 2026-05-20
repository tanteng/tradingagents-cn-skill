# 步骤键名映射 schema

本文档是机器可读配置 `step_schema.json` 的说明文档。
所有中英文键名映射、字段约束均定义在此文件中。

## 中文 ↔ 英文步骤名映射

| 中文步骤名 | 英文步骤名 | 说明 |
|-----------|-----------|------|
| 多头分析 | bull_analyst | 多头分析师 |
| 空头分析 | bear_analyst | 空头分析师 |
| 技术分析 | tech_analyst | 技术分析师 |
| 基本面分析 | fundamentals_analyst | 基本面分析师 |
| 新闻分析 | news_analyst | 新闻分析师 |
| 社交媒体分析 | social_analyst | 社交媒体分析师 |
| 辩论过程 | debate | 多空辩论 |
| 研究经理决策 | manager | 研究经理 |
| 交易计划 | trader | 交易员 |
| 风险辩论 | risk_debate | 三方风险辩论 |
| 风险经理决策 | risk_manager | 风险经理 |

## 各步骤必填字段

### 多头分析 / bull_analyst

中文结构（共享 JSON，顶层平铺）：
```json
{
  "core_logic": "string - 核心逻辑（1-2句话）",
  "bull_case": ["string - 论点1", "string - 论点2"],
  "risk_alert": "string - 风险提示",
  "confidenceindex": "number 0-1 - 信心指数"
}
```

旧结构（嵌套在 bull_detail，供兼容）：
```json
{
  "bull_detail": {
    "core_logic": "string",
    "bull_case": ["string"],
    "risk_alert": "string",
    "confidenceindex": "number"
  },
  "analysis": ["string"]
}
```

### 空头分析 / bear_analyst

中文结构：
```json
{
  "core_logic": "string",
  "bear_case": ["string"],
  "valuation_risk": "string - 估值风险",
  "downside_risk": "string - 下行风险",
  "technical_alert": "string - 技术面警示",
  "fundamental_concerns": "string - 基本面担忧",
  "risk_events": "string - 风险事件",
  "confidenceindex": "number"
}
```

### 技术分析 / tech_analyst

```json
{
  "趋势判断": { "短期": "多头/空头/震荡", "中期": "...", "长期": "..." },
  "关键指标": { "MA5": "string", "MA10": "string", "RSI": "string", "MACD": "string" },
  "技术信号总结": "string（≤50字）",
  "操作建议": { "支撑位": "string", "压力位": "string", "止损位": "string" }
}
```

### 基本面分析 / fundamentals_analyst

```json
{
  "估值分析": {
    "当前市盈率（P/E）": "string",
    "同业比较": "string",
    "PEG指标": "string",
    "股息率": "string",
    "总结": "string"
  },
  "盈利能力": { "毛利率": {"数值": "string", "同比变化": "string"}, ... },
  "成长性": { "营收增速": "string", "净利润增速": "string", "PEG": "string" },
  "财务健康": { "资产负债率": "string", "流动比率": "string", "经营现金流": "string" },
  "综合评价": "string"
}
```

### 新闻分析 / news_analyst

```json
{
  "news_list": [
    {
      "title": "string",
      "date": "YYYY-MM-DD",
      "source": "string",
      "summary": "string（≤50字，不能为空）",
      "sentiment": "偏多/偏空/中性"
    }
  ],
  "news_count": "number",
  "sentiment": "偏多/偏空/中性"
}
```

### 社交媒体分析 / social_analyst

```json
{
  "sentiment_score": "number 0-1",
  "platforms": [
    { "name": "string", "sentiment": "string", "heat": "string" }
  ]
}
```

### 辩论过程 / debate

```json
{
  "rounds": [
    {
      "round": 1,
      "bull_points": ["string"],
      "bear_points": ["string"]
    }
  ]
}
```

### 研究经理决策 / manager

```json
{
  "decision": "买入/卖出/持有",
  "rationale": "string（1-2句话）"
}
```

### 交易计划 / trader

```json
{
  "decision": "买入/卖出/持有",
  "buy_price": "number|null",
  "target_price": "number|null",
  "stop_loss": "number|null",
  "position_size": "string（如 15%-20%）",
  "entry_criteria": "string",
  "exit_criteria": "string"
}
```

**注意**：decision="买入"时 buy_price/target_price/stop_loss 必填数字；持有/观望时设为 null。

### 风险辩论 / risk_debate

```json
{
  "aggressive": { "position": "激进派", "position_size": "string", "target_return": "string", "stop_loss": "string" },
  "neutral": { "position": "中性派", "position_size": "string", "target_return": "string", "stop_loss": "string" },
  "conservative": { "position": "保守派", "position_size": "string", "target_return": "string", "stop_loss": "string" }
}
```

### 风险经理决策 / risk_manager

```json
{
  "final_recommendation": "买入/卖出/持有",
  "risk_level": "低/中/高",
  "investment_horizon": "短期/中期/长期",
  "risk_assessment": {
    "市场风险": "string",
    "流动性风险": "string",
    "波动性风险": "string"
  },
  "suitable_investors": ["稳健型", "积极型"],
  "monitoring_points": ["string"]
}
```