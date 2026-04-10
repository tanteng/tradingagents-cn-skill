---
name: tradingagents-cn-skill
version: 1.0.0
description: >
  多智能体股票分析报告生成（TradingAgents 架构）。
  通过 4 位分析师报告 + 2 轮多空辩论 + 研究管理者裁决 + 交易员计划 + 3 方风控辩论 + 投资组合经理最终决策，
  生成专业 PDF 报告（五级评级体系）。
  触发场景：用户要求分析股票、生成股票报告、提供截图或代码进行分析、
  询问买卖建议、要求技术分析或基本面分析或风险评估。
metadata:
  openclaw:
    emoji: "📊"
    requires:
      bins: ["python3"]
---

# TradingAgents-CN Skill

多智能体股票分析框架。Agent 串行完成 17 步分析，参照 TradingAgents 论文架构：
分析师团队 → 多空辩论（2轮）→ 研究管理者裁决 → 交易员 → 风控三方辩论 → 投资组合经理最终决策 → PDF 报告。

## 全局规则

### 重试协议

每次 LLM 调用后，**必须**通过 `validate_step.py` 验证输出：

```bash
echo '<LLM原始输出>' | python3 {baseDir}/scripts/validate_step.py --step <步骤名> --stock-code <股票代码> --attempt <次数>
```

**处理规则：**
- `exit 0` → stdout 是清洗后的 JSON，保存结果，进入下一步
- `exit 1` → stderr 是 JSON 错误信息（含 `hint` 字段），将 hint 追加到 prompt 重新调用 LLM
- 关键步骤（bull_r1、bear_r1、bull_r2、bear_r2、manager、trader、risk_aggressive、risk_conservative、risk_neutral、portfolio_manager）最多重试 **3 次**
- 次要步骤（tech、fundamentals、news、social）最多重试 **2 次**
- 超过重试上限 → 获取默认值继续：
  ```bash
  python3 {baseDir}/scripts/validate_step.py --step <步骤名> --default
  ```

**重试时的 prompt 追加格式：**
```
注意：上次输出格式有误。{hint}。请严格按要求的格式返回。
```

### LLM 调用失败重试

如果 LLM 调用本身失败（返回空、网络超时、API 错误等非格式问题），**必须**执行以下重试：

1. 等待 **5 秒**后重新调用同一步骤，使用相同的 prompt
2. 最多重试 **2 次**（共 3 次尝试）
3. 如果 3 次都失败：
   - JSON 步骤：获取默认值继续（`validate_step.py --default`）
   - 辩论步骤：使用占位文本 "该角色分析暂时不可用，请参考其他角色的分析。"
4. 此规则适用于**所有步骤**，包括辩论步骤（Step 7-10、Step 13-15）

### 辩论步骤的特殊处理

辩论步骤（bull_r1、bear_r1、bull_r2、bear_r2、risk_aggressive、risk_conservative、risk_neutral）输出为**纯中文文本**，不要求 JSON 格式，不需要通过 validate_step.py 验证。直接保存文本内容即可。

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
Step 1A: 获取原始文本（截图 → OCR / 文字 → 直接使用）
Step 1B: 结构化提取 LLM → validate → stock_data JSON
Step 2:  web_search 获取新闻 → news_data
───── 阶段一：四位分析师报告 ─────
Step 3:  技术/市场分析师 LLM → validate → tech_analyst
Step 4:  基本面分析师 LLM → validate → fundamentals_analyst
Step 5:  新闻分析师 LLM → validate → news_analyst
Step 6:  社交媒体/情绪分析师 LLM → validate → social_analyst
───── 阶段二：多空辩论（2轮）─────
Step 7:  看多研究员 Round 1 LLM → bull_r1（纯文本）
Step 8:  看空研究员 Round 1 LLM → bear_r1（纯文本）
Step 9:  看多研究员 Round 2 LLM → bull_r2（纯文本，回应bear_r1）
Step 10: 看空研究员 Round 2 LLM → bear_r2（纯文本，回应bull_r2）
───── 阶段三：研究管理者裁决 ─────
Step 11: 研究管理者 LLM → validate → manager_decision
───── 阶段四：交易员 ─────
Step 12: 交易员 LLM → validate → trading_plan
───── 阶段五：风控三方辩论 ─────
Step 13: 激进型风控分析师 LLM → risk_aggressive（纯文本）
Step 14: 保守型风控分析师 LLM → risk_conservative（纯文本）
Step 15: 中立型风控分析师 LLM → risk_neutral（纯文本）
───── 阶段六：最终决策 ─────
Step 16: 投资组合经理 LLM → validate → final_decision
───── 阶段七：报告生成 ─────
Step 17: 组装 JSON → 生成 PDF
```

---

## Step 1A: 获取原始文本

根据用户输入类型，获取原始文本：

**情况 1：用户提供截图/图片**
- 调用 OCR MCP tool（如 `image-ocr`）或 Agent 内建的图片识别能力
- 将识别结果作为原始文本

**情况 2：用户提供文字描述**
- 直接使用用户提供的文字作为原始文本

**情况 3：用户只提供股票代码/名称**
- 将股票代码和名称作为原始文本，后续步骤会通过 web_search 补充数据

---

## Step 1B: 结构化数据提取

**LLM 调用：**
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

**验证：**
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step step1b --stock-code {股票代码} --attempt 1
```

---

## Step 2: 获取新闻数据

使用 web_search 工具搜索该股票的最新新闻。搜索查询：
1. `{股票名称} 最新消息 2026`
2. `{股票代码} 研报 评级`
3. `{行业关键词} 行业动态`

将搜索结果整理为 JSON 数组：
```json
{
  "news_list": [
    {"title": "新闻标题", "date": "日期", "source": "来源", "summary": "摘要", "sentiment": "偏多/中性/偏空"},
    ...
  ]
}
```

---

## Step 3: 技术/市场分析师

**LLM 调用：**
- system_prompt: 读取 `references/tech_prompt.md`
- user_message:
  ```
  请分析以下股票的技术面：

  {stock_data JSON（Step 1B 结果）}

  请根据已有的技术指标数据，选择最相关的指标进行深度分析，以纯 JSON 格式返回。
  ```

**验证：**
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step tech --stock-code {股票代码} --attempt 1
```

---

## Step 4: 基本面分析师

**LLM 调用：**
- system_prompt: 读取 `references/fundamentals_prompt.md`
- user_message:
  ```
  请分析以下公司的基本面：

  {stock_data JSON}

  补充新闻信息：
  {news_data JSON 中与财报/业绩相关的新闻}

  请进行全面的基本面分析，以纯 JSON 格式返回。
  ```

**验证：**
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step fundamentals --stock-code {股票代码} --attempt 1
```

---

## Step 5: 新闻分析师

**LLM 调用：**
- system_prompt: 读取 `references/news_prompt.md`
- user_message:
  ```
  请分析以下股票的新闻面：

  股票信息：{stock_data JSON}
  近期新闻：{news_data JSON}

  请综合分析新闻对该股票的影响，以纯 JSON 格式返回。
  ```

**验证：**
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step news --stock-code {股票代码} --attempt 1
```

---

## Step 6: 社交媒体/情绪分析师

**LLM 调用：**
- system_prompt: 读取 `references/social_prompt.md`
- user_message:
  ```
  请分析以下股票的市场情绪：

  股票信息：{stock_data JSON}
  近期新闻（含情绪标签）：{news_data JSON}

  请综合分析社交媒体舆情和公众情绪，以纯 JSON 格式返回。
  ```

**验证：**
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step social --stock-code {股票代码} --attempt 1
```

---

## Step 7: 看多研究员 Round 1

**LLM 调用：**
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

**不验证**，直接保存 LLM 输出文本为 `bull_r1`。

---

## Step 8: 看空研究员 Round 1

**LLM 调用：**
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
  {bull_r1 文本}

  这是第一轮辩论。请基于分析报告构建你的看空论证，并回应看多方的观点。
  ```

**不验证**，直接保存 LLM 输出文本为 `bear_r1`。

---

## Step 9: 看多研究员 Round 2

**LLM 调用：**
- system_prompt: 读取 `references/bull_prompt.md`
- user_message:
  ```
  这是第二轮辩论。请回应看空研究员的论点：

  四份分析师报告（同上，简要引用关键数据即可）。

  辩论历史：
  看多 Round 1：{bull_r1}
  看空 Round 1：{bear_r1}

  看空研究员上一轮论点：
  {bear_r1 文本}

  请针对看空方的每个具体论点进行回应和反驳，展示为什么看多立场更有说服力。
  ```

**不验证**，直接保存为 `bull_r2`。

---

## Step 10: 看空研究员 Round 2

**LLM 调用：**
- system_prompt: 读取 `references/bear_prompt.md`
- user_message:
  ```
  这是第二轮辩论。请回应看多研究员的论点：

  辩论历史：
  看多 Round 1：{bull_r1}
  看空 Round 1：{bear_r1}
  看多 Round 2：{bull_r2}

  看多研究员上一轮论点：
  {bull_r2 文本}

  请针对看多方的每个具体论点进行回应和反驳，展示为什么看空立场更有说服力。
  ```

**不验证**，直接保存为 `bear_r2`。

---

## Step 11: 研究管理者裁决

**LLM 调用：**
- system_prompt: 读取 `references/manager_prompt.md`
- user_message:
  ```
  请评估以下多空辩论，做出你的裁决：

  完整辩论记录：
  === 看多研究员 Round 1 ===
  {bull_r1}

  === 看空研究员 Round 1 ===
  {bear_r1}

  === 看多研究员 Round 2 ===
  {bull_r2}

  === 看空研究员 Round 2 ===
  {bear_r2}

  请做出明确的决策（买入/卖出/持有），并制定详细的投资计划。以纯 JSON 格式返回。
  ```

**验证：**
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step manager --stock-code {股票代码} --attempt 1
```

---

## Step 12: 交易员计划

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

**验证：**
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step trader --stock-code {股票代码} --attempt 1
```

---

## Step 13: 激进型风控分析师

**LLM 调用：**
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
  这是第一位发言，尚无其他风控分析师的观点。
  ```

**不验证**，直接保存为 `risk_aggressive`。

---

## Step 14: 保守型风控分析师

**LLM 调用：**
- system_prompt: 读取 `references/risk_conservative_prompt.md`
- user_message:
  ```
  交易员的交易计划：
  {trading_plan JSON}

  参考数据（同上摘要）。

  激进型分析师的观点：
  {risk_aggressive 文本}

  请从保守型风险分析师的角度评估此交易计划，并回应激进派的观点。
  ```

**不验证**，直接保存为 `risk_conservative`。

---

## Step 15: 中立型风控分析师

**LLM 调用：**
- system_prompt: 读取 `references/risk_neutral_prompt.md`
- user_message:
  ```
  交易员的交易计划：
  {trading_plan JSON}

  参考数据（同上摘要）。

  激进型分析师的观点：
  {risk_aggressive 文本}

  保守型分析师的观点：
  {risk_conservative 文本}

  请从中立型风险分析师的角度评估此交易计划，平衡激进派和保守派的观点。
  ```

**不验证**，直接保存为 `risk_neutral`。

---

## Step 16: 投资组合经理（最终决策）

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
  {risk_aggressive}

  保守型分析师：
  {risk_conservative}

  中立型分析师：
  {risk_neutral}

  请使用五级评级（买入/增持/持有/减持/卖出），以纯 JSON 格式返回最终决策。
  ```

**验证：**
```bash
echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step portfolio_manager --stock-code {股票代码} --attempt 1
```

---

## Step 17: 生成 PDF 报告

将所有结果组装为完整 JSON（格式详见 `references/data_schema.md`）：

```json
{
  "stock_code": "{股票代码}",
  "stock_name": "{股票名称}",
  "current_price": "{当前价格}",
  "timestamp": "{ISO 8601 时间戳}",
  "parallel_analysis": {
    "tech_analyst": "{Step 3 结果}",
    "fundamentals_analyst": "{Step 4 结果}",
    "news_analyst": "{Step 5 结果}",
    "social_analyst": "{Step 6 结果}"
  },
  "investment_debate": {
    "bull_r1": "{Step 7 文本}",
    "bear_r1": "{Step 8 文本}",
    "bull_r2": "{Step 9 文本}",
    "bear_r2": "{Step 10 文本}"
  },
  "manager_decision": "{Step 11 结果}",
  "trading_plan": "{Step 12 结果}",
  "risk_debate": {
    "aggressive": "{Step 13 文本}",
    "conservative": "{Step 14 文本}",
    "neutral": "{Step 15 文本}"
  },
  "final_decision": "{Step 16 结果}"
}
```

调用脚本生成 PDF：

```bash
echo '<完整JSON>' | python3 {baseDir}/scripts/adapt_data.py | python3 {baseDir}/scripts/generate_report.py --stdin
```

脚本输出 PDF 文件路径。

**重要：必须将 PDF 文件直接发送给用户，不要只显示文件路径。** 使用文件发送能力将 PDF 作为附件发给用户。

同时附上简要的分析摘要：
- 评级（五级：买入/增持/持有/减持/卖出）
- 关键价格：买入价、目标价、止损价
- 风险等级和投资期限
- 一句话投资论文

---

## 输出文件

PDF 保存到 `{baseDir}/scripts/reports/`，文件名格式：`{股票代码}_{YYYYMMDD}_{HHMMSS}.pdf`

---

## 调试方法

### CLI 直接触发
```bash
openclaw agent --message "分析一下 PDD" --verbose on --json
```

### 单步验证工具
```bash
# 测试某个 LLM 输出是否通过验证
echo '{"report":"test","key_points":["p1"],"indicators":{}}' | python3 {baseDir}/scripts/validate_step.py --step tech

# 获取某步骤的默认值
python3 {baseDir}/scripts/validate_step.py --step tech --default
```

### 日志查看
```bash
cat {baseDir}/scripts/logs/{股票代码}_*.log
```
