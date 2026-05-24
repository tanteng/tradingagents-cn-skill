# tradingagents-cn-skill

基于 OpenClaw Skill 框架的股票分析工具，通过多智能体辩论机制生成专业股票分析 PDF 报告。

## 架构 v3.0

**Phase 2 架构：文件交换 + Subagent 并行**。核心改进是把"上下文传参"改为"文件系统交换"，彻底斩断因上下文过长导致的格式丢失和 Token 浪费。

```
中间层文件（所有 subagent 共用同一个 JSON）
{baseDir}/scripts/intermediate/{股票代码}_{时间戳}.json
```

**Agent 流程**：
```
主 Agent（协调）
  ├── Step 1: 初始化 JSON 文件
  ├── Step 2: 并行 spawn 6 个分析师 subagent
  │           ├── BullAgent    → 写 "结果.多头分析"
  │           ├── BearAgent    → 写 "结果.空头分析"
  │           ├── TechAgent    → 写 "结果.技术分析"
  │           ├── FundAgent    → 写 "结果.基本面分析"
  │           ├── NewsAgent    → 写 "结果.新闻分析"
  │           └── SocialAgent  → 写 "结果.社交媒体分析"
  ├── 轮询等待所有 subagent 完成
  ├── Step 3: 研究经理（读文件）→ 写 "结果.研究经理决策"
  ├── Step 4: 交易员（读文件）→ 写 "结果.交易计划"
  ├── Step 5: 风险辩论（读文件）→ 写 "结果.风险辩论"
  ├── Step 6: 风险经理（读文件）→ 写 "结果.风险经理决策"
  └── Step 7: 生成 PDF（读文件）
```

## 功能特性

- **6 个专业分析师**：多头 / 空头 / 技术 / 基本面 / 新闻 / 社交媒体
- **辩论决策机制**：研究经理主持多空辩论，给出买入/卖出/持有决策
- **交易计划制定**：包含目标价位和仓位建议
- **三方风险评估**：激进/中性/保守三派辩论
- **专业 PDF 报告**：生成完整分析报告
- **内容质量检测**：字数约束确保输出充实（bull_case ≥50字/core_logic ≥20字）
- **完善日志**：每步输入/输出/验证结果均记录到日志文件

## 文件结构

```
tradingagents-cn-skill/
├── SKILL.md                      # Skill 定义（Agent 完整流程）
├── README.md                     # 本文件
├── references/                  # Prompt 文件
│   ├── bull_prompt.md            # 多头分析师
│   ├── bear_prompt.md            # 空头分析师
│   ├── tech_prompt.md            # 技术分析师
│   ├── fundamentals_prompt.md    # 基本面分析师
│   ├── news_prompt.md            # 新闻分析师
│   ├── social_prompt.md          # 社交媒体分析师
│   ├── manager_prompt.md         # 研究经理
│   ├── trader_prompt.md         # 交易员
│   ├── risk_debate_prompt.md     # 风险辩论
│   ├── risk_manager_prompt.md   # 风险经理
│   ├── step_schema.md            # 步骤键名映射
│   └── data_schema.md            # 数据 schema
├── scripts/
│   ├── intermediate_shared.py   # 中间层文件读写（各 subagent 写入自己的字段）
│   ├── validate_step.py         # JSON 验证 + 内容质量检测 + 日志
│   ├── generate_report.py        # PDF 生成入口
│   ├── pdf_generator.py         # PDF 生成核心
│   ├── intermediate/            # 中间层 JSON 文件目录
│   └── reports/                 # 生成的 PDF 目录
└── _meta.json                    # 元数据
```

## 内容质量约束

`validate_step.py` 在字段验证后还会检查内容质量：

| 步骤 | 字段 | 最小字数 |
|------|------|---------|
| bull_analyst | core_logic | ≥20字 |
| bull_analyst | bull_case 总计 | ≥50字 |
| bear_analyst | core_logic | ≥20字 |
| bear_analyst | bear_case 总计 | ≥50字 |
| tech_analyst | 技术信号总结 | ≥50字 |
| fundamentals_analyst | 综合评价 | ≥80字 |
| manager | rationale | ≥30字 |

## 工作流程

```
Step 1:  初始化 JSON 文件
Step 2:  6 个分析师并行（新闻搜索 + LLM 分析 + 验证 + 写入）
Step 3:  研究经理决策（多空辩论汇总）
Step 4:  交易员计划（目标价/止损/仓位）
Step 5:  风险辩论（激进/中性/保守三派）
Step 6:  风险经理决策（最终风控建议）
Step 7:  生成 PDF 报告
```

## 调试

### CLI 触发完整流程
```bash
openclaw agent --message "分析一下 PDD" --verbose on --json
```

### 查看当前分析状态
```bash
python3 scripts/intermediate_shared.py --stock-code PDD --status
```

### 查看共享文件内容
```bash
python3 scripts/intermediate_shared.py --stock-code PDD --read
```

### 测试验证（含内容质量检测）
```bash
echo '{"bull_detail": {"core_logic": "测试", "bull_case": ["测试"]}}' | \
  python3 scripts/validate_step.py --step bull_analyst
```

### 获取默认值
```bash
python3 scripts/validate_step.py --step bull_analyst --default
```

### 直接生成 PDF（已有共享文件时）
```bash
python3 scripts/generate_report.py \
  --from-file scripts/intermediate/PDD_20260520_100000.json
```

### 日志查看
```bash
cat scripts/logs/latest.log
```

## 版本历史

- **v3.0.0** — Phase 2 文件交换架构 + 6 并行分析师 + 内容质量检测
- **v2.0.0** — 统一为 Agent 驱动模式，新增 validate_step.py
- **v1.1.0** — 六分析师并行执行优化，JSON 解析重试机制