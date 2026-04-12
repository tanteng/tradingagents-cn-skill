---
name: tradingagents-cn-skill
version: 2.0.0
description: >
  分析股票并生成 PDF 报告。当用户提到以下任何一种意图时触发：
  分析股票、股票分析、生成PDF、生成报告、股票报告、分析一下、
  看看这只股票、帮我分析、技术分析、基本面分析、买卖建议、
  风险评估、多空分析、投资建议。
  支持输入：股票截图、股票代码、股票名称、行情文字描述。
  输出：多智能体深度分析 PDF 报告（技术面+基本面+新闻+情绪+多空辩论+风控评估+五级评级）。
metadata:
  openclaw:
    emoji: "📊"
    requires:
      bins: ["python3"]
---

# TradingAgents-CN Skill v3

多智能体股票分析框架。Agent **在主进程中串行**完成 10 步分析，参照 TradingAgents 论文架构：
四位分析师（1次调用）→ 多空辩论（2轮）→ 研究管理者裁决 → 交易员 → 风控三方辩论 → 投资组合经理最终决策 → PDF 报告。

## 全局规则

### ⚠️ 禁止 SubAgent（最高优先级）

**所有步骤必须在主 Agent 进程中串行执行，禁止使用 subagent、子任务、并行 agent 或任何形式的任务分派。**

原因：本 Skill 的每一步都依赖前面步骤的完整输出（stock_data → 分析师报告 → 辩论 → 决策）。SubAgent 不共享上下文，会导致数据丢失（如新闻为空、技术指标缺失）。

**具体要求：**
- 不要使用 `dispatching-parallel-agents` 或类似机制
- 不要把任何步骤委托给其他 agent 或 worker
- 所有 LLM 调用、web_search、脚本执行都在同一个 agent 会话中完成
- 每一步的结果必须保存在当前会话的变量/上下文中，供后续步骤直接引用

### 执行模式

**全程自动执行，不询问用户。** 遇到错误自动重试（最多 3 次），某步失败使用默认值继续，只在最终输出 PDF 和摘要。

### 验证与数据存储策略

**每步 LLM 调用后必须 validate + save。** `validate_step.py --save` 会验证输出并自动写入 `results/{stock_code}_report.json` 的对应字段。

**Step 1 完成后初始化 report.json：**
```bash
python3 {baseDir}/scripts/validate_step.py --init '{"stock_code":"<code>","stock_name":"<name>","current_price":<price>,"news_data":<Step2的news_data>}' --stock-code <code>
```

**每步 validate 命令格式：**
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step <步骤名> --stock-code <code> --save
```

辩论 Round 2 需要加 `--round 2`：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step bull_debate --stock-code <code> --round 2 --save
```

验证失败（exit 1）→ 将 stderr 中的 hint 追加到 prompt 重试，最多 3 次。全部失败 → 用默认值：
```bash
python3 {baseDir}/scripts/validate_step.py --step <步骤名> --default
```

### 日志

分析开始前，设置日志环境变量：
```bash
export TRADINGAGENTS_LOG_FILE="{baseDir}/scripts/logs/{股票代码}_{YYYYMMDD}_{HHMMSS}.log"
mkdir -p {baseDir}/scripts/logs
```

### 语言要求

所有 LLM 调用的 system_prompt 和 user_message 使用**中文**。所有分析内容使用**中文**输出。

---

## 工作流程

```
Step 1: 获取原始文本 + 结构化提取 → stock_data JSON
Step 2: web_search + web_fetch 获取新闻 → news_data
───── 阶段一：四位分析师报告（1次LLM调用）─────
Step 3: 四位分析师综合分析 LLM → tech/fundamentals/news/social
───── 阶段二：多空辩论（2轮）─────
Step 4: 看多研究员 Round 1 + 看空研究员 Round 1
Step 5: 看多研究员 Round 2 + 看空研究员 Round 2
───── 阶段三：研究管理者裁决 + 交易员 ─────
Step 6: 研究管理者裁决 LLM → manager_decision
Step 7: 交易员计划 LLM → trading_plan
───── 阶段四：风控三方辩论 ─────
Step 8: 激进 + 保守 + 中立三方风控辩论
───── 阶段五：最终决策 ─────
Step 9: 投资组合经理（最终决策）LLM → final_decision（验证 rating）
───── 阶段六：报告生成 ─────
Step 10: 组装 JSON → 生成 PDF
```

---

## Step 1: 获取原始文本 + 结构化提取

根据用户输入类型获取原始文本：

**情况 1：用户提供截图/图片**
- 使用 Agent 内建的图片识别能力读取文字
- 将识别结果作为原始文本

**情况 2：用户提供文字描述**
- 直接使用用户提供的文字作为原始文本

**情况 3：用户只提供股票代码/名称**
- 将股票代码和名称作为原始文本，后续步骤通过 web_search 补充数据

**LLM 调用：结构化数据提取**
- system_prompt:
  ```
  你是股票数据提取专家。从用户提供的文本（可能来自截图OCR、交易软件、财报等）中，
  提取结构化的股票数据。只提取文本中明确存在的信息，缺失的字段设为 null。
  不要虚构或推测任何数据。以纯 JSON 格式返回。
  ```
- user_message:
  ```
  请从以下文本中提取股票数据，以纯 JSON 格式返回：

  {原始文本}

  要求返回的 JSON 格式：
  {
    "stock_code": "股票代码（如 PDD、600519、00700.HK）",
    "stock_name": "股票名称",
    "current_price": 数字或null,
    "change_pct": "涨跌幅字符串或null",
    "volume": "成交量或null",
    "turnover": "成交额或null",
    "technical_indicators": {
      "MA5": 数字或null, "MA10": 数字或null, "MA20": 数字或null,
      "MA30": 数字或null, "MA60": 数字或null, "MA120": 数字或null,
      "RSI": 数字或null,
      "MACD": "MACD描述或null",
      "KDJ": "KDJ描述或null",
      "BOLL_upper": 数字或null, "BOLL_mid": 数字或null, "BOLL_lower": 数字或null
    },
    "fundamentals": {
      "PE": 数字或null, "PB": 数字或null, "ROE": "百分比或null",
      "market_cap": "市值或null", "revenue": "营收或null", "net_profit": "净利润或null"
    },
    "k_line_pattern": "K线形态描述或null",
    "other_info": "其他信息或null"
  }
  ```

---

## Step 2: 获取新闻数据

使用 web_search 工具搜索该股票的最新新闻，**至少搜索 3 个查询**：
1. `{股票名称} {股票代码} 最新消息 2026`
2. `{股票代码} stock news latest`
3. `{股票名称} 研报 评级`

**对每条搜索结果**：调用 web_fetch 获取正文摘要（前 200 字）。

将搜索结果整理为 JSON 数组，**保存为变量 `news_data`**：
```json
{
  "news_list": [
    {"title": "新闻标题", "date": "日期", "source": "来源", "summary": "至少50字的摘要", "sentiment": "偏多/中性/偏空", "url": "原文链接"},
    ...
  ]
}
```

**关键约束**：
- `news_list` 数组**至少包含 3 条新闻**，不足则追加搜索
- `summary` 字段不得为空，最少 50 字
- 如果实在搜不到，设置 `news_list` 为空数组但 `sentiment` 设为 "暂无数据"

**⚠️ 重要**：`news_data` 变量必须在 Step 10 组装 JSON 时写入 `"news_data"` 字段，否则 PDF 报告中新闻部分会为空。

---

## Step 3: 四位分析师综合分析（1次LLM调用）

**LLM 调用：**
- system_prompt: 读取 `references/combined_analysts_prompt.md`
- user_message:
  ```
  请对以下股票进行四维度综合分析：

  股票数据：
  {stock_data JSON（Step 1 结果）}

  近期新闻：
  {news_data JSON（Step 2 结果）}

  请同时从技术面、基本面、新闻面、情绪面四个角度深度分析，以纯 JSON 格式返回。
  ```

LLM 将一次性返回包含 `tech_analyst`、`fundamentals_analyst`、`news_analyst`、`social_analyst` 四个对象的 JSON。

**验证并保存**：将返回的 JSON 中每个分析师的输出分别 validate + save：
```bash
echo '<tech_analyst部分>' | python3 {baseDir}/scripts/validate_step.py --step tech --stock-code {股票代码} --save
echo '<fundamentals_analyst部分>' | python3 {baseDir}/scripts/validate_step.py --step fundamentals --stock-code {股票代码} --save
echo '<news_analyst部分>' | python3 {baseDir}/scripts/validate_step.py --step news --stock-code {股票代码} --save
echo '<social_analyst部分>' | python3 {baseDir}/scripts/validate_step.py --step social --stock-code {股票代码} --save
```

**如果某个分析师输出异常**（空、非 JSON、缺字段），validate 会 exit 1 并给 hint，重试或使用默认值：
```bash
python3 {baseDir}/scripts/validate_step.py --step tech --default
python3 {baseDir}/scripts/validate_step.py --step fundamentals --default
python3 {baseDir}/scripts/validate_step.py --step news --default
python3 {baseDir}/scripts/validate_step.py --step social --default
```

---

## Step 4: 多空辩论 Round 1

**一次消息内连续完成两个 LLM 调用：**

### 4A: 看多研究员 Round 1

- system_prompt: 读取 `references/bull_prompt.md`
- user_message:
  ```
  请基于以下四份分析师报告，作为看多研究员发表你的第一轮论证：

  技术/市场分析报告：
  {tech_analyst 的 report 字段}

  基本面分析报告：
  {fundamentals_analyst 的 report 字段}

  新闻分析报告：
  {news_analyst 的 report 字段}

  社交媒体/情绪分析报告：
  {social_analyst 的 report 字段}

  这是第一轮辩论，尚无看空方论点。请基于以上分析报告构建你的看多论证。
  ```

**验证并保存 bull_r1**：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step bull_debate --stock-code {股票代码} --round 1 --save
```

### 4B: 看空研究员 Round 1

- system_prompt: 读取 `references/bear_prompt.md`
- user_message:
  ```
  请基于以下四份分析师报告，作为看空研究员发表你的第一轮论证：

  技术/市场分析报告：
  {tech_analyst 的 report 字段}

  基本面分析报告：
  {fundamentals_analyst 的 report 字段}

  新闻分析报告：
  {news_analyst 的 report 字段}

  社交媒体/情绪分析报告：
  {social_analyst 的 report 字段}

  看多研究员的论点：
  {bull_r1 的 debate_text}

  这是第一轮辩论。请基于分析报告构建你的看空论证，并回应看多方的观点。
  ```

**验证并保存 bear_r1**：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step bear_debate --stock-code {股票代码} --round 1 --save
```

---

## Step 5: 多空辩论 Round 2

### 5A: 看多研究员 Round 2

- system_prompt: 读取 `references/bull_prompt.md`
- user_message:
  ```
  这是第二轮辩论。请回应看空研究员的论点：

  辩论历史：
  看多 Round 1：{bull_r1 的 debate_text}
  看空 Round 1：{bear_r1 的 debate_text}

  请针对看空方的每个具体论点进行回应和反驳。
  ```

**验证并保存 bull_r2**：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step bull_debate --stock-code {股票代码} --round 2 --save
```

### 5B: 看空研究员 Round 2

- system_prompt: 读取 `references/bear_prompt.md`
- user_message:
  ```
  这是第二轮辩论。请回应看多研究员的论点：

  辩论历史：
  看多 Round 1：{bull_r1 的 debate_text}
  看空 Round 1：{bear_r1 的 debate_text}
  看多 Round 2：{bull_r2 的 debate_text}

  请针对看多方的每个具体论点进行回应和反驳。
  ```

**验证并保存 bear_r2**：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step bear_debate --stock-code {股票代码} --round 2 --save
```

---

## Step 6: 研究管理者裁决

**LLM 调用：**
- system_prompt: 读取 `references/manager_prompt.md`
- user_message:
  ```
  请评估以下多空辩论，做出你的裁决：

  完整辩论记录：
  === 看多研究员 Round 1 ===
  {bull_r1 的 debate_text}

  === 看空研究员 Round 1 ===
  {bear_r1 的 debate_text}

  === 看多研究员 Round 2 ===
  {bull_r2 的 debate_text}

  === 看空研究员 Round 2 ===
  {bear_r2 的 debate_text}

  请做出明确的决策（买入/卖出/持有），并制定详细的投资计划。以纯 JSON 格式返回。
  ```

**验证并保存**：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step manager --stock-code {股票代码} --save
```

---

## Step 7: 交易员计划

**LLM 调用：**
- system_prompt: 读取 `references/trader_prompt.md`
- user_message:
  ```
  基于分析师团队的综合分析，以下是为 {股票名称}（当前价格：{current_price}）制定的投资计划：

  研究管理者的投资计划：
  {manager_decision JSON}

  请基于此计划，制定具体的交易方案。以纯 JSON 格式返回。
  所有价格必须是具体数字。
  ```

**验证并保存**：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step trader --stock-code {股票代码} --save
```

---

## Step 8: 风控三方辩论

**连续完成三个 LLM 调用：**

### 8A: 激进型风控分析师

- system_prompt: 读取 `references/risk_aggressive_prompt.md`
- user_message:
  ```
  交易员的交易计划：
  {trading_plan JSON}

  参考数据：
  技术分析摘要：{tech_analyst 的 key_points}
  基本面摘要：{fundamentals_analyst 的 key_points}
  新闻摘要：{news_analyst 的 key_points}
  情绪摘要：{social_analyst 的 key_points}

  请从激进型风险分析师的角度评估此交易计划。
  ```

**验证并保存**：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step risk_aggressive --stock-code {股票代码} --save
```

### 8B: 保守型风控分析师

- system_prompt: 读取 `references/risk_conservative_prompt.md`
- user_message:
  ```
  交易员的交易计划：
  {trading_plan JSON}

  参考数据（同上摘要）。

  激进型分析师的观点：
  {risk_aggressive 的 debate_text}

  请从保守型风险分析师的角度评估此交易计划，并回应激进派的观点。
  ```

**验证并保存**：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step risk_conservative --stock-code {股票代码} --save
```

### 8C: 中立型风控分析师

- system_prompt: 读取 `references/risk_neutral_prompt.md`
- user_message:
  ```
  交易员的交易计划：
  {trading_plan JSON}

  参考数据（同上摘要）。

  激进型分析师的观点：
  {risk_aggressive 的 debate_text}

  保守型分析师的观点：
  {risk_conservative 的 debate_text}

  请从中立型风险分析师的角度评估此交易计划，平衡激进派和保守派的观点。
  ```

**验证并保存**：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step risk_neutral --stock-code {股票代码} --save
```

---

## Step 9: 投资组合经理（最终决策）

**LLM 调用：**
- system_prompt: 读取 `references/risk_manager_prompt.md`
- user_message:
  ```
  请综合以下信息，做出最终投资决策：

  标的：{股票代码} {股票名称}，当前价格：{current_price}

  研究管理者的投资计划：
  {manager_decision JSON}

  交易员的交易提案：
  {trading_plan JSON}

  === 风控分析师辩论记录 ===

  激进型分析师：
  {risk_aggressive 的 debate_text}

  保守型分析师：
  {risk_conservative 的 debate_text}

  中立型分析师：
  {risk_neutral 的 debate_text}

  请使用五级评级（买入/增持/持有/减持/卖出），以纯 JSON 格式返回最终决策。
  ```

**此步必须验证**：
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step portfolio_manager --stock-code {股票代码} --attempt 1 --save
```

- `exit 0` → 通过，继续
- `exit 1` → 将 hint 追加到 prompt 重新调用 LLM，最多重试 **3 次**
- 超过 3 次 → 使用默认值：
  ```bash
  python3 {baseDir}/scripts/validate_step.py --step portfolio_manager --default --stock-code {股票代码} --save
  ```

---

## Step 10: 生成 PDF 报告

**所有步骤的数据已通过 `--save` 自动写入 `results/{stock_code}_report.json`。** 直接生成 PDF：

```bash
python3 {baseDir}/scripts/generate_report.py --input {baseDir}/scripts/results/{股票代码}_report.json
```

如果命令失败（exit code != 0），检查日志后重试一次。

**必须将 PDF 文件直接发送给用户。** 使用文件发送能力将 PDF 作为附件发给用户。

同时附上简要的分析摘要：
- 评级（五级：买入/增持/持有/减持/卖出）
- 关键价格：买入价、目标价、止损价
- 风险等级和投资期限
- 一句话投资论文
---

## 输出文件

PDF 默认保存到 `{baseDir}/scripts/reports/`，文件名格式：`{股票代码}_{YYYYMMDD}_{HHMMSS}.pdf`

可通过 `--output-dir` 指定输出到用户工作目录。

---

## 调试方法

### 单步验证工具
```bash
# 测试某个 LLM 输出是否通过验证
echo '{"rating":"买入","executive_summary":"摘要","investment_thesis":"论文","risk_level":"中"}' | python3 {baseDir}/scripts/validate_step.py --step portfolio_manager

# 获取某步骤的默认值
python3 {baseDir}/scripts/validate_step.py --step tech --default
```

### 日志查看
```bash
cat {baseDir}/scripts/logs/{股票代码}_*.log
```
