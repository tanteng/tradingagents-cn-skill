# TradingAgents-CN Skill

多智能体股票分析报告生成框架。借鉴 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 项目架构，通过 6 个分析师并行分析 + 多空辩论 + 交易计划 + 风险评估，生成专业的股票分析 PDF 报告。

**版本**: 3.0.0

---

## 核心特性

- **6 个分析师并行执行** — 利用 subagent 并行处理，显著提升分析速度
- **5 档评级体系** — Buy/Overweight/Hold/Underweight/Sell，与原始 TradingAgents 项目一致
- **多空辩论机制** — 2 轮辩论后由研究经理给出最终决策
- **三方风险辩论** — 激进派/中性派/保守派多角度风险评估
- **LLM 输出验证** — 每步 LLM 调用后通过 `validate_step.py` 验证，确保数据质量
- **中文输出** — 所有分析内容使用中文

---

## 架构

```
主 Agent (当前 session)
  │
  ├── Step 1-2: 获取股票数据 + 新闻 (串行)
  │
  ├── sessions_spawn 6个分析师并行 (fork):
  │     ├── bull_analyst (LLM + validate)
  │     ├── bear_analyst (LLM + validate)
  │     ├── tech_analyst (LLM + validate)
  │     ├── fundamentals_analyst (LLM + validate)
  │     ├── news_analyst (LLM + validate)
  │     └── social_analyst (LLM + validate)
  │
  ├── 汇合结果，继续串行:
  ├── Step 9:  多空辩论 + 研究经理决策
  ├── Step 10: 交易员计划
  ├── Step 11: 风险辩论 + 风险经理评估
  └── Step 12: 生成 PDF
```

---

## 目录结构

```
tradingagents-cn-skill/
├── SKILL.md                      # Skill 定义文件 (OpenClaw skill)
├── README.md                     # 本文件
├── scripts/
│   ├── generate_report.py        # PDF 报告生成脚本
│   ├── pdf_generator.py          # PDF 生成器 (HTML → PDF)
│   ├── validate_step.py          # LLM 输出验证脚本
│   └── logs/                     # 分析日志目录
├── references/
│   ├── bull_prompt.md            # 多头分析师 prompt
│   ├── bear_prompt.md            # 空头分析师 prompt
│   ├── tech_prompt.md            # 技术分析师 prompt
│   ├── fundamentals_prompt.md    # 基本面分析师 prompt
│   ├── news_prompt.md            # 新闻分析师 prompt
│   ├── social_prompt.md          # 社交媒体分析师 prompt
│   ├── manager_prompt.md         # 研究经理 prompt (5档评级)
│   ├── trader_prompt.md          # 交易员 prompt
│   ├── risk_manager_prompt.md    # 风险经理 prompt (5档评级)
│   ├── risk_debate_prompt.md     # 三方风险辩论 prompt
│   └── data_schema.md            # JSON 数据格式定义
└── reports/                      # 生成的 PDF 报告目录
```

---

## 与原始 TradingAgents 项目的差异

| 特性 | 原始项目 | 本 Skill |
|-----|---------|---------|
| 执行方式 | LangGraph 图编排 | Shell 脚本 + subagent |
| 输出语言 | 英文 | 中文 |
| 分析师数量 | 4 个 (market/sentiment/news/fundamentals) | 6 个 (+ tech/social) |
| 评级体系 | 5 档 (Buy/Overweight/Hold/Underweight/Sell) | 5 档 (对齐) |
| 辩论轮次 | 1 轮 | 2 轮 |
| 验证方式 | Pydantic + structured output | validate_step.py 脚本 |
| 数据源 | yfinance | westock-data CLI |
| 记忆系统 | TradingMemoryLog (历史决策) | 暂未实现 |

---

## 安装

### 前置要求

- Python 3.8+
- OpenClaw agent 系统
- `westock-data` 包 (用于获取股票数据)

### 安装 skill

通过 ClawHub 安装：

```bash
openclaw skill install tradingagents-cn-skill
```

或手动复制到 `~/.openclaw/skills/skills/tradingagents-cn-skill/`

### 安装 westock-data

```bash
pip install westock-data-clawhub
```

---

## 使用方法

### 通过 OpenClaw CLI

```bash
openclaw agent --message "分析一下腾讯 00700.HK" --verbose off --json
```

### 通过 Skill 触发

当用户消息匹配以下场景时自动激活：
- "分析股票"、"生成股票报告"
- "股票技术分析"、"股票基本面分析"
- "股票风险评估"、"股票买卖建议"
- 提供截图或代码进行分析

---

## 输出示例

PDF 报告包含：
- **执行摘要** — 核心结论 (5档评级)、关键价格、风险等级
- **技术分析** — MA5/MA10/RSI/MACD 等指标
- **基本面分析** — 营收、净利润、ROE、PE 等
- **新闻情绪** — 最新新闻摘要及情绪判断
- **多空辩论** — 2 轮辩论记录
- **交易计划** — 买入价、目标价、止损价、仓位建议
- **风险评估** — 三方风险辩论 + 风险经理最终决策

---

## 数据格式

### manager_decision (研究经理决策)

```json
{
  "recommendation": "买入/增持/持有/减持/卖出",
  "rationale": "核心逻辑",
  "strategic_actions": "交易员执行步骤"
}
```

### final_decision (风险经理最终决策)

```json
{
  "rating": "Buy/Overweight/Hold/Underweight/Sell",
  "risk_level": "低/中/高",
  "investment_horizon": "短期(1-4周)/中期(1-6个月)/长期(6个月以上)",
  "executive_summary": "简洁行动计划",
  "investment_thesis": "详细推理依据",
  "price_target": 数字或null,
  "time_horizon": "3-6个月",
  "risk_assessment": {...},
  "suitable_investors": ["激进型", "稳健型"],
  "monitoring_points": [...]
}
```

---

## 调试

### 查看日志

```bash
cat ~/.openclaw/skills/skills/tradingagents-cn-skill/scripts/logs/latest.log
```

### 验证 LLM 输出

```bash
echo '{"bull_detail":{"core_logic":"test","bull_case":["point1"]}}' | \
  python3 ~/.openclaw/skills/skills/tradingagents-cn-skill/scripts/validate_step.py \
  --step bull_analyst
```

### 获取默认值

```bash
python3 ~/.openclaw/skills/skills/tradingagents-cn-skill/scripts/validate_step.py \
  --step bull_analyst --default
```

---

## License

MIT License

---

## 参考

- [TradingAgents (原始项目)](https://github.com/TauricResearch/TradingAgents)
- [OpenClaw 文档](https://docs.openclaw.ai)
- [ClawHub](https://clawhub.ai)