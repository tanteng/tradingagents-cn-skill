# 最终报告 JSON Schema（完整类型定义）

Agent 执行 13 步后，将所有结果组装为以下 JSON 结构传给 `generate_report.py`。

**核心原则**：每个字段的类型是确定的，不存在"可能是 string 也可能是 dict"的情况。

## 完整 JSON 结构

```json
{
  "stock_code": "string — 股票代码（如 002594、NET、00700.HK）← Step 1B",
  "stock_name": "string — 股票名称（如 比亚迪、Cloudflare）← Step 1B",
  "current_price": "number — 当前价格（如 101.67）← Step 1B",
  "timestamp": "string — ISO 时间戳 ← 组装时生成",

  "news_data": {
    "news_list": "array<object> — 新闻列表 ← Step 2 web_search"
  },

  "parallel_analysis": {
    "tech_analyst": "object — Step 3 的完整 JSON 输出（见下方）",
    "fundamentals_analyst": "object — Step 4 的完整 JSON 输出（见下方）",
    "news_analyst": "object — Step 5 的完整 JSON 输出（见下方）",
    "social_analyst": "object — Step 6 的完整 JSON 输出（见下方）"
  },

  "investment_debate": {
    "bull_r1": "object — Step 7 看多R1 的完整 JSON 输出（见下方）",
    "bear_r1": "object — Step 7 看空R1 的完整 JSON 输出（见下方）",
    "bull_r2": "object — Step 8 看多R2 的完整 JSON 输出（见下方）",
    "bear_r2": "object — Step 8 看空R2 的完整 JSON 输出（见下方）"
  },

  "manager_decision": "object — Step 9 研究管理者的完整 JSON 输出（见下方）",
  "trading_plan": "object — Step 10 交易员的完整 JSON 输出（见下方）",

  "risk_debate": {
    "aggressive": "object — Step 11 激进型的完整 JSON 输出（见下方）",
    "conservative": "object — Step 11 保守型的完整 JSON 输出（见下方）",
    "neutral": "object — Step 11 中立型的完整 JSON 输出（见下方）"
  },

  "final_decision": "object — Step 12 投资组合经理的完整 JSON 输出（见下方）"
}
```

## 各字段的精确类型

### parallel_analysis.tech_analyst（Step 3）

| 字段 | 类型 | 说明 |
|------|------|------|
| report | string | 技术分析报告（500字以上中文 markdown） |
| key_points | string[] | 要点数组 |
| indicators | object | `{趋势方向: string, 支撑位: string, 压力位: string, RSI: string, MACD信号: string, 均线排列: string, 成交量配合: string}` |
| 技术信号总结 | string | 50字以内总结 |
| 操作建议 | object | `{支撑位: string, 压力位: string, 止损位: string}` |

### parallel_analysis.fundamentals_analyst（Step 4）

| 字段 | 类型 | 说明 |
|------|------|------|
| report | string | 基本面报告（500-2000字 markdown） |
| key_points | string[] | 要点数组 |
| financials | object | **固定英文 key**：`{pe: string, pb: string, roe: string, gross_margin: string, net_margin: string, revenue_growth: string, debt_ratio: string}` |
| valuation_summary | string | 估值总结 |
| fundamental_rating | string | 枚举：优秀/良好/一般/较差/恶化 |

### parallel_analysis.news_analyst（Step 5）

| 字段 | 类型 | 说明 |
|------|------|------|
| report | string | 新闻分析报告（500字以上 markdown） |
| key_points | string[] | 要点数组 |
| 新闻情绪 | string | 枚举：偏多/中性/偏空 |
| 关键催化剂 | string[] | 催化剂数组 |
| 风险事件 | string[] | 风险事件数组 |

### parallel_analysis.social_analyst（Step 6）

| 字段 | 类型 | 说明 |
|------|------|------|
| report | string | 情绪分析报告（500字以上 markdown） |
| key_points | string[] | 要点数组 |
| sentiment_score | number | 0-1 浮点数 |
| 情绪趋势 | string | 枚举：上升/稳定/下降 |
| 舆情总结 | string | 50字以内 |

### investment_debate.bull_r1 / bull_r2（Step 7, 8）

| 字段 | 类型 | 说明 |
|------|------|------|
| debate_text | string | 看多论述（500-2000字 markdown） |
| core_logic | string | 核心看多逻辑 |
| bull_case | string[] | 3-5 个论点 |
| confidence | number | 0-1 浮点数 |
| risk_acknowledgement | string | 需注意的风险 |

### investment_debate.bear_r1 / bear_r2（Step 7, 8）

| 字段 | 类型 | 说明 |
|------|------|------|
| debate_text | string | 看空论述（500-2000字 markdown） |
| core_logic | string | 核心看空逻辑 |
| bear_case | string[] | 3-5 个论点 |
| confidence | number | 0-1 浮点数 |
| bull_counterpoint | string | 对多头的反驳 |

### manager_decision（Step 9）

| 字段 | 类型 | 说明 |
|------|------|------|
| recommendation | string | 枚举：买入/卖出/持有 |
| rationale | string | 决策理由（200字以上） |
| investment_plan | string | 投资计划（200字以上） |
| bull_strength | string | 看多方最强论点 |
| bear_strength | string | 看空方最强论点 |
| key_risks | string[] | 风险数组 |

### trading_plan（Step 10）

| 字段 | 类型 | 说明 |
|------|------|------|
| decision | string | 枚举：买入/观望/卖出 |
| buy_price | number \| null | 买入价（观望时 null） |
| target_price | number \| null | 目标价（观望时 null） |
| stop_loss | number \| null | 止损价（观望时 null） |
| reference_price | number | 当前参考价 |
| reference_target | number | 参考目标价 |
| reference_stop | number | 参考止损价 |
| position_size | string | 仓位百分比 |
| entry_criteria | string | 入场条件 |
| exit_criteria | string | 出场条件 |

### risk_debate.aggressive / conservative / neutral（Step 11）

| 字段 | 类型 | 说明 |
|------|------|------|
| debate_text | string | 风控论述（300-1000字 markdown） |
| stance | string | 立场描述 |
| position_size | string | 建议仓位 |
| target_return | string | 目标收益 |
| stop_loss | string | 止损 |
| key_points | string[] | 核心论点数组 |

### final_decision（Step 12）

| 字段 | 类型 | 说明 |
|------|------|------|
| rating | string | **五级评级**：买入/增持/持有/减持/卖出 |
| executive_summary | string | 执行摘要（200字以上） |
| investment_thesis | string | 投资论文（300字以上） |
| risk_level | string | 枚举：低/中/高 |
| investment_horizon | string | 枚举：短期/中期/长期 |
| risk_assessment | object | `{市场风险: string, 流动性风险: string, 波动性风险: string}` |
| suitable_investors | string[] | 适合的投资者类型 |
| monitoring_points | string[] | 监控要点 |

## ⚠️ 关键约束

1. **所有 debate_text / report 字段**：类型是 `string`，内容是 markdown 格式的中文文本
2. **所有 JSON 输出**：是 `object`（JSON 对象），不是 JSON 字符串。Agent 把 LLM 返回的 JSON 解析后直接放入对应字段
3. **financials 的 key**：必须是固定英文（pe/pb/roe/gross_margin/net_margin/revenue_growth/debt_ratio）
4. **null 只出现在 trading_plan**：当 decision 为"观望"或"卖出"时，buy_price/target_price/stop_loss 为 null
5. **不允许嵌套 JSON 字符串**：不要把 `{"debate_text": "..."}` 作为字符串塞进 bull_r1，而是直接作为 object
