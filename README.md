
# TradingAgents-CN Skill

基于 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 论文架构的中文股票多智能体分析框架。通过 4 位分析师 + 2 轮多空辩论 + 风控三方辩论 + 五级评级，生成专业中文 PDF 分析报告。

> 灵感来源：[TradingAgents: Multi-Agents LLM Financial Trading Framework](https://arxiv.org/abs/2412.20138)（Yijia Xiao et al., 2025）

## 架构

**Agent 驱动模式**：所有 LLM 调用由 OpenClaw Agent 框架完成，脚本负责验证（validate）、数据存储（--save）和 PDF 生成。

```
用户输入（股票代码/截图/文字）
  │
  ▼
┌─────────────────────────────────────────┐
│  阶段一：数据获取                          │
│  结构化提取 → web_search 获取新闻          │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  阶段二：四位分析师                        │
│  技术分析师 → 基本面分析师                  │
│  → 新闻分析师 → 情绪分析师                  │
│  每步: LLM → validate --save → report.json │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  阶段三：多空辩论（2轮）                    │
│  🐂 看多 R1 → 🐻 看空 R1                  │
│  → 🐂 看多 R2 → 🐻 看空 R2                │
│  每步: LLM → validate --save → report.json │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  阶段四：研究管理者 + 交易员                │
│  ⚖️ 研究管理者裁决 → 💹 交易员计划          │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  阶段五：风控三方辩论                       │
│  🔴 激进派 → 🟢 保守派 → 🟡 中立派         │
│        👔 投资组合经理最终决策               │
│        （五级评级）                         │
└──────────────────┬──────────────────────┘
                   ▼
              📄 PDF 报告
```

## 数据流设计

**确定性数据管线**：每步 LLM 输出 → validate_step.py 验证 → 自动写入 report.json → generate_report.py 读取生成 PDF。

```
Agent LLM 调用
      ↓
echo '<输出>' | python3 validate_step.py --step <name> --stock-code <code> --save
      ↓
  validate_step.py:
    1. 解析 JSON
    2. 验证必填字段
    3. exit 0 → 写入 results/{code}_report.json 对应字段
    3. exit 1 → stderr 返回 hint，Agent 重试
      ↓
最后一步:
  python3 generate_report.py --input results/{code}_report.json
      ↓
  PDF 文件
```

**设计原则**：
- 所有 JSON key 使用英文（不允许中文 key）
- Prompt 定义 schema → validate 验证 → pdf_generator 读取，三端对齐
- 每步 validate --save 自动写入 report.json，Agent 不需要手动组装大 JSON
- 辩论步骤也输出结构化 JSON（含 debate_text Markdown 长文本字段）

## 核心特性

| 特性 | 说明 |
|------|------|
| **4 位专业分析师** | 技术/市场、基本面、新闻、社交媒体/情绪 |
| **2 轮多空辩论** | Bull/Bear 互相引用对方论点进行对话式辩论 |
| **研究管理者裁决** | 辩论裁判，"不要默认 Hold"，必须给出明确立场 |
| **交易员计划** | 具体数字的买入价/目标价/止损价 |
| **风控三方辩论** | 激进/保守/中立三种风险偏好独立发言互相辩驳 |
| **五级评级** | 买入 / 增持 / 持有 / 减持 / 卖出 |
| **中文 PDF 报告** | Markdown 渲染，支持粗体/标题/列表/表格 |
| **validate --save** | 每步自动验证 + 写入 report.json |
| **全局重试** | LLM 失败等 5 秒重试最多 2 次，格式错误带 hint 重试 |

## 文件结构

```
tradingagents-cn-skill/
├── SKILL.md                          # Skill 定义（Agent 10 步流程）
├── README.md
├── _meta.json
├── references/                       # 各角色 Prompt（定义 JSON schema）
│   ├── tech_prompt.md                # 技术/市场分析师
│   ├── fundamentals_prompt.md        # 基本面分析师
│   ├── news_prompt.md                # 新闻分析师
│   ├── social_prompt.md              # 社交媒体/情绪分析师
│   ├── bull_prompt.md                # 看多研究员
│   ├── bear_prompt.md                # 看空研究员
│   ├── manager_prompt.md             # 研究管理者
│   ├── trader_prompt.md              # 交易员
│   ├── risk_aggressive_prompt.md     # 激进型风控
│   ├── risk_conservative_prompt.md   # 保守型风控
│   ├── risk_neutral_prompt.md        # 中立型风控
│   ├── risk_manager_prompt.md        # 投资组合经理
│   └── data_schema.md                # 完整 JSON 数据格式定义
└── scripts/
    ├── validate_step.py              # 验证 + --save 写入 report.json
    ├── generate_report.py            # PDF 生成入口（--input）
    ├── pdf_generator.py              # PDF 生成核心（HTML → PDF）
    └── __init__.py
```

## 工作流程

```
Step 1:   结构化数据提取 → validate --init（创建 report.json）
Step 2:   web_search 获取新闻 → validate --save
Step 3:   技术分析师 → validate --step tech --save
Step 4:   基本面分析师 → validate --step fundamentals --save
Step 5:   新闻分析师 → validate --step news --save
Step 6:   情绪分析师 → validate --step social --save
Step 7:   看多 R1 → validate --step bull_debate --round 1 --save
          看空 R1 → validate --step bear_debate --round 1 --save
Step 8:   看多 R2 → validate --step bull_debate --round 2 --save
          看空 R2 → validate --step bear_debate --round 2 --save
Step 9:   研究管理者 → validate --step manager --save
          交易员 → validate --step trader --save
          激进风控 → validate --step risk_aggressive --save
          保守风控 → validate --step risk_conservative --save
          中立风控 → validate --step risk_neutral --save
          投资组合经理 → validate --step portfolio_manager --save
Step 10:  python3 generate_report.py --input results/{code}_report.json → PDF
```

## 与 TradingAgents 原版的对比

| 维度 | TradingAgents 原版 | 本项目 |
|------|-------------------|--------|
| 编排方式 | LangGraph StateGraph | OpenClaw SKILL.md Agent 驱动 |
| 语言 | 英文 | **中文** |
| 辩论机制 | Bull/Bear N轮 + 风控三方 | Bull/Bear **2轮** + 风控三方 |
| 评级体系 | Buy/Overweight/Hold/Underweight/Sell | 买入/增持/持有/减持/卖出 |
| 输出格式 | 终端文本 | **PDF 报告** |
| 数据管线 | LangGraph State 自动流转 | validate --save 逐步写入 report.json |
| LLM 后端 | OpenAI/Google/Anthropic | MiniMax / 可配置 |

## 使用方法

### 通过 OpenClaw 触发
```bash
openclaw agent --message "分析一下小米 01810.HK" --verbose on
```

### 从已有 report.json 生成 PDF
```bash
python3 scripts/generate_report.py --input scripts/results/01810_report.json
```

### 单步验证测试
```bash
# 验证并保存
echo '{"report":"报告","key_points":["要点"]}' | python3 scripts/validate_step.py --step tech --stock-code TEST --save

# 获取默认值
python3 scripts/validate_step.py --step tech --default
```

## 免责声明

本框架仅供研究和学习目的，不构成任何形式的投资建议。投资有风险，入市需谨慎。
