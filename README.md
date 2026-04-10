
# TradingAgents-CN Skill

基于 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 论文架构的中文股票多智能体分析框架。通过 4 位分析师 + 2 轮多空辩论 + 风控三方辩论 + 五级评级，生成专业中文 PDF 分析报告。

> 灵感来源：[TradingAgents: Multi-Agents LLM Financial Trading Framework](https://arxiv.org/abs/2412.20138)（Yijia Xiao et al., 2025）

## 架构

**Agent 驱动模式**：所有 LLM 调用由 OpenClaw Agent 框架完成，脚本只负责 JSON 验证和 PDF 生成。

```
用户输入（股票代码/截图/文字）
  │
  ▼
┌─────────────────────────────────────────┐
│  阶段一：四位分析师                        │
│  技术分析师 → 基本面分析师                  │
│  → 新闻分析师 → 情绪分析师                  │
│        （各自输出深度分析报告）              │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  阶段二：多空辩论（2轮）                    │
│  🐂 看多 R1 → 🐻 看空 R1                  │
│  → 🐂 看多 R2（回应Bear）                  │
│  → 🐻 看空 R2（回应Bull）                  │
│        ⚖️ 研究管理者裁决                    │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  阶段三：交易员                            │
│  制定具体价格的交易计划                     │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  阶段四：风控三方辩论                       │
│  🔴 激进派 → 🟢 保守派 → 🟡 中立派         │
│        👔 投资组合经理最终决策               │
│        （五级评级）                         │
└──────────────────┬──────────────────────┘
                   ▼
              📄 PDF 报告
```

## 核心特性

| 特性 | 说明 |
|------|------|
| **4 位专业分析师** | 技术/市场、基本面、新闻、社交媒体/情绪 |
| **2 轮多空辩论** | Bull/Bear 互相引用对方论点进行对话式辩论 |
| **研究管理者裁决** | 辩论裁判，"不要默认 Hold"，必须给出明确立场 |
| **交易员计划** | 具体数字的买入价/目标价/止损价 |
| **风控三方辩论** | 激进/保守/中立三种风险偏好独立发言互相辩驳 |
| **五级评级** | 买入 / 增持 / 持有 / 减持 / 卖出 |
| **中文 PDF 报告** | 完整的专业分析报告 |
| **自动重试** | LLM 输出验证失败时自动重试，带错误提示 |
| **完善日志** | 每步输入/输出/验证结果均记录到日志文件 |

## 文件结构

```
tradingagents-cn-skill/
├── SKILL.md                          # Skill 定义（Agent 17 步流程）
├── README.md                         # 本文件
├── _meta.json                        # 元数据
├── references/                       # 各角色 Prompt 文件
│   ├── tech_prompt.md                # 技术/市场分析师
│   ├── fundamentals_prompt.md        # 基本面分析师
│   ├── news_prompt.md                # 新闻分析师
│   ├── social_prompt.md              # 社交媒体/情绪分析师
│   ├── bull_prompt.md                # 看多研究员（支持多轮辩论）
│   ├── bear_prompt.md                # 看空研究员（支持多轮辩论）
│   ├── manager_prompt.md             # 研究管理者（辩论裁判）
│   ├── trader_prompt.md              # 交易员
│   ├── risk_aggressive_prompt.md     # 激进型风控分析师
│   ├── risk_conservative_prompt.md   # 保守型风控分析师
│   ├── risk_neutral_prompt.md        # 中立型风控分析师
│   ├── risk_manager_prompt.md        # 投资组合经理（最终决策）
│   └── data_schema.md                # JSON 数据格式定义
├── scripts/
│   ├── validate_step.py              # JSON 验证 + 日志工具
│   ├── adapt_data.py                 # 数据适配层
│   ├── generate_report.py            # PDF 生成入口
│   ├── pdf_generator.py              # PDF 生成核心
│   ├── logs/                         # 分析日志目录
│   └── reports/                      # 生成的 PDF 报告
```

## 17 步工作流程

```
Step 1A:  获取原始文本（截图OCR / 文字 / 股票代码）
Step 1B:  结构化数据提取 → validate → stock_data
Step 2:   web_search 获取新闻 → news_data
───── 阶段一：四位分析师报告 ─────
Step 3:   技术/市场分析师 → validate → tech_analyst
Step 4:   基本面分析师 → validate → fundamentals_analyst
Step 5:   新闻分析师 → validate → news_analyst
Step 6:   社交媒体/情绪分析师 → validate → social_analyst
───── 阶段二：多空辩论（2轮）─────
Step 7:   看多研究员 Round 1 → bull_r1（纯文本）
Step 8:   看空研究员 Round 1 → bear_r1（纯文本）
Step 9:   看多研究员 Round 2 → bull_r2（回应bear_r1）
Step 10:  看空研究员 Round 2 → bear_r2（回应bull_r2）
───── 阶段三：研究管理者裁决 ─────
Step 11:  研究管理者 → validate → manager_decision
───── 阶段四：交易员 ─────
Step 12:  交易员 → validate → trading_plan
───── 阶段五：风控三方辩论 ─────
Step 13:  激进型风控分析师 → risk_aggressive（纯文本）
Step 14:  保守型风控分析师 → risk_conservative（纯文本）
Step 15:  中立型风控分析师 → risk_neutral（纯文本）
───── 阶段六：最终决策 ─────
Step 16:  投资组合经理 → validate → final_decision（五级评级）
───── 阶段七：报告生成 ─────
Step 17:  组装 JSON → 生成 PDF
```

## 与 TradingAgents 原版的对比

| 维度 | TradingAgents 原版 | 本项目 |
|------|-------------------|--------|
| 编排方式 | LangGraph StateGraph | OpenClaw SKILL.md Agent 驱动 |
| 语言 | 英文 | **中文** |
| 辩论机制 | Bull/Bear N轮 + 风控三方 | Bull/Bear **2轮** + 风控三方 |
| 评级体系 | Buy/Overweight/Hold/Underweight/Sell | 买入/增持/持有/减持/卖出 |
| 输出格式 | 终端文本 | **PDF 报告** |
| LLM 后端 | OpenAI/Google/Anthropic | MiniMax / 可配置 |
| 数据工具 | Alpha Vantage API | web_search + 用户输入 |

## 使用方法

### CLI 触发完整流程
```bash
openclaw agent --message "分析一下 PDD" --verbose on --json
```

### 单步验证测试
```bash
# 测试技术分析师输出
echo '{"report":"测试报告","key_points":["要点1"]}' | python3 scripts/validate_step.py --step tech

# 测试五级评级验证
echo '{"rating":"买入","executive_summary":"摘要","investment_thesis":"论文","risk_level":"中"}' | python3 scripts/validate_step.py --step portfolio_manager

# 获取默认值
python3 scripts/validate_step.py --step tech --default
```

### 日志查看
```bash
ls scripts/logs/
cat scripts/logs/{股票代码}_*.log
```

## 免责声明

本框架仅供研究和学习目的，不构成任何形式的投资建议。投资有风险，入市需谨慎。
