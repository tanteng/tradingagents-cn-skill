
# tradingagents-cn-skill

基于 OpenClaw Skill 框架的股票分析工具，通过多智能体辩论机制生成专业股票分析 PDF 报告。

## 架构

**Agent 驱动模式**：所有 LLM 调用由 Agent 框架完成，脚本只负责 JSON 验证和 PDF 生成。

```
Agent (串行 12 步 LLM 调用)
  │
  ├── validate_step.py (每步验证 JSON + 日志)
  │
  └── generate_report.py (最终生成 PDF)
```

## 功能特性

- **6 个专业分析师**：多头 / 空头 / 技术 / 基本面 / 新闻 / 社交媒体
- **辩论决策机制**：研究经理主持多空辩论，给出买入/卖出/持有决策
- **交易计划制定**：包含目标价位和仓位建议
- **三方风险评估**：激进/中性/保守三派辩论
- **专业 PDF 报告**：生成完整分析报告
- **自动重试**：LLM 输出验证失败时自动重试，带错误提示
- **完善日志**：每步输入/输出/验证结果均记录到日志文件

## 文件结构

```
tradingagents-cn-skill/
├── SKILL.md                    # Skill 定义（Agent 12 步流程）
├── README.md                   # 本文件
├── _meta.json                  # 元数据
├── references/                 # 各角色 Prompt 文件
│   ├── bull_prompt.md
│   ├── bear_prompt.md
│   ├── tech_prompt.md
│   ├── fundamentals_prompt.md
│   ├── news_prompt.md
│   ├── social_prompt.md
│   ├── manager_prompt.md
│   ├── trader_prompt.md
│   ├── risk_debate_prompt.md
│   ├── risk_manager_prompt.md
│   └── data_schema.md
├── scripts/
│   ├── validate_step.py        # JSON 验证 + 日志工具
│   ├── generate_report.py      # PDF 生成入口
│   ├── pdf_generator.py        # PDF 生成核心
│   └── logs/                   # 分析日志目录
└── assets/                     # 静态资源
```

## 工作流程

```
Step 1:  解析输入 → text_description
Step 2:  web_search 获取新闻 → news_data
Step 3:  多头分析师 → validate → bull_analyst
Step 4:  空头分析师 → validate → bear_analyst
Step 5:  技术分析师 → validate → tech_analyst
Step 6:  基本面分析师 → validate → fundamentals_analyst
Step 7:  新闻分析师 → validate → news_analyst
Step 8:  社交媒体分析师 → validate → social_analyst
Step 9:  多空辩论 + 研究经理决策 → validate
Step 10: 交易员计划 → validate
Step 11: 风险辩论 + 风险经理评估 → validate
Step 12: 组装 JSON → 生成 PDF
```

## 调试

### CLI 触发完整流程
```bash
openclaw agent --message "分析一下 PDD" --verbose on --json
```

### 单步验证测试
```bash
echo '{"bull_detail":{"core_logic":"test","bull_case":["point1"]}}' | python3 scripts/validate_step.py --step bull_analyst
```

### 获取默认值
```bash
python3 scripts/validate_step.py --step bull_analyst --default
```

### 日志查看
```bash
cat scripts/logs/latest.log
```

## 版本历史

- **v2.0.0** — 统一为 Agent 驱动模式，新增 validate_step.py，删除独立 LLM 调用脚本
- **v1.1.0** — 六分析师并行执行优化，JSON 解析重试机制
