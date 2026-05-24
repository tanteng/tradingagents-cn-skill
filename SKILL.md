---
name: tradingagents-cn-skill
version: 3.0.0
description: >
  股票多智能体分析报告生成。通过 6 个分析师 subagent 并行分析 + 文件交换 + Assembler 组装，
  生成专业 PDF 报告。触发场景：用户要求分析股票、生成股票报告、询问买卖建议。
metadata:
  openclaw:
    emoji: "📊"
    requires:
      bins: ["python3"]
---

# TradingAgents-CN Skill v3.0

Phase 2 架构：文件交换 + Subagent 并行。核心改进是把"上下文传参"改为"文件系统交换"，
彻底斩断因上下文过长导致的格式丢失和 Token 浪费。

## 核心设计

### 文件架构

```
{baseDir}/scripts/intermediate/{股票代码}_{时间戳}.json
```

整个分析共用**一个 JSON 文件**，每个 subagent 只写自己专属的字段：

```json
{
  "stock_code": "PDD",
  "stock_name": "拼多多",
  "current_price": 99.54,
  "timestamp": "2026-05-20T10:00:00+08:00",
  "news_data": [...],
  "status": {
    "新闻数据": "done", "多头分析": "done", "空头分析": "done",
    "技术分析": "pending", "基本面分析": "pending", ...
  },
  "结果": {
    "多头分析": { "core_logic": "...", "bull_case": [...], "confidenceindex": 0.75 },
    "空头分析": { "core_logic": "...", "bear_case": [...], "confidenceindex": 0.65 },
    ...
  }
}
```

### Agent 架构

```
主 Agent（协调）
  ├── Step 1: 初始化 JSON 文件
  ├── Step 2: 并行 spawn 6 个分析师 subagent
  │           ├── BullAgent  → 写 "结果.多头分析"
  │           ├── BearAgent  → 写 "结果.空头分析"
  │           ├── TechAgent  → 写 "结果.技术分析"
  │           ├── FundAgent  → 写 "结果.基本面分析"
  │           ├── NewsAgent  → 写 "结果.新闻分析"
  │           └── SocialAgent → 写 "结果.社交媒体分析"
  ├── 等待所有 subagent 完成
  ├── Step 3: 研究经理 subagent（读文件）→ 写 "结果.研究经理决策"
  ├── Step 4: 交易员 subagent（读文件）→ 写 "结果.交易计划"
  ├── Step 5: 风险辩论 subagent → 写 "结果.风险辩论"
  ├── Step 6: 风险经理 subagent → 写 "结果.风险经理决策"
  └── Step 7: 生成 PDF（读文件）
```

---

## 主 Agent 工作流

### Step 1: 初始化

```bash
JSON_FILE=$(python3 {baseDir}/scripts/intermediate_shared.py \
  --init --stock-code {股票代码} --stock-name {股票名称})
echo "中间文件: $JSON_FILE"
```

### Step 2: 并行 spawn 6 个分析师

**使用 `sessions_spawn`** 并行启动 6 个 subagent，每个 subagent：
1. 读取自己的 prompt 文件（references/xxx_prompt.md）
2. 根据股票代码搜索新闻（web_search）
3. 调用 LLM 分析
4. 验证输出（validate_step.py）
5. 用 `intermediate_shared.py --write` 把结果写入共享 JSON 文件
6. **不返回任何内容给主 Agent**，只返回完成状态

```bash
# 并行 spawn 示例伪代码：
# BullAgent:   sessions_spawn(task="分析多头...", env={JSON_FILE, ...})
# BearAgent:   sessions_spawn(task="分析空头...", env={JSON_FILE, ...})
# TechAgent:   sessions_spawn(task="技术分析...", env={JSON_FILE, ...})
# FundAgent:   sessions_spawn(task="基本面分析...", env={JSON_FILE, ...})
# NewsAgent:   sessions_spawn(task="新闻分析...", env={JSON_FILE, ...})
# SocialAgent: sessions_spawn(task="社交媒体分析...", env={JSON_FILE, ...})
```

**主 Agent 轮询等待所有分析师完成**：

```bash
# Step 2 完成后，轮询等待 6 个分析师全部 done
echo "等待 6 个分析师完成..."
for i in {1..30}; do  # 最多等 30 次（约 2.5 分钟）
  DONE_COUNT=$(python3 {baseDir}/scripts/intermediate_shared.py \
    --stock-code {股票代码} --status 2>/dev/null | grep -c " done$" || echo 0)
  if [ "$DONE_COUNT" -ge 6 ]; then
    echo "所有分析师完成（$DONE_COUNT/6），进入研究经理决策"
    break
  fi
  echo "进度: $DONE_COUNT/6 已完成，等待..."
  sleep 5  # 每 5 秒轮询一次
done
if [ "$DONE_COUNT" -lt 6 ]; then
  echo "警告: 等待超时，$DONE_COUNT/6 分析师完成，部分数据可能缺失"
fi
```

**Subagent 指令模板**（每个 agent 替换自己的部分）：

```
你是一个专业的股票分析师。你需要：

1. 读取共享数据文件：{JSON_FILE}
2. 读取你的分析 prompt：{references/xxx_prompt.md}
3. 从 JSON 文件中获取 current_price、stock_code、stock_name、text_description
4. 使用 web_search 搜索近期新闻（{股票代码} {股票名称} 最新新闻）
5. 基于 prompt 和数据，调用 LLM 生成分析结果（JSON 格式）
6. 验证输出：echo '<LLM输出>' | python3 {baseDir}/scripts/validate_step.py --step {步骤名} --stock-code {股票代码} --attempt 1
7. 写入结果：
   python3 {baseDir}/scripts/intermediate_shared.py \
     --write --step {步骤名} --data '<验证后的JSON>'
8. 完成后输出：分析完成，{步骤名} 已写入共享文件
```

### Step 3: 研究经理决策

```bash
# 等待研究经理完成（单步串行，直接等待即可）
echo "等待研究经理决策..."
for i in {1..20}; do
  STATUS=$(python3 {baseDir}/scripts/intermediate_shared.py --stock-code {股票代码} --status 2>/dev/null)
  if echo "$STATUS" | grep -q "研究经理决策.*done"; then
    echo "研究经理决策完成，进入交易员计划"
    break
  fi
  sleep 3
done
```

### Step 4: 交易员计划

从共享文件读取 `研究经理决策` 和 `current_price`，调用 LLM → 验证 → 写入 `结果.交易计划`。

```bash
# 等待交易员完成
for i in {1..20}; do
  STATUS=$(python3 {baseDir}/scripts/intermediate_shared.py --stock-code {股票代码} --status 2>/dev/null)
  if echo "$STATUS" | grep -q "交易计划.*done"; then
    echo "交易员计划完成，进入风险辩论"
    break
  fi
  sleep 3
done
```

### Step 5: 风险辩论 + 风险经理决策

同理，依次 spawn 或串行执行，将结果写入 `结果.风险辩论` 和 `结果.风险经理决策`。

```bash
# 等待风险辩论完成
for i in {1..20}; do
  STATUS=$(python3 {baseDir}/scripts/intermediate_shared.py --stock-code {股票代码} --status 2>/dev/null)
  if echo "$STATUS" | grep -q "风险辩论.*done"; then
    echo "风险辩论完成，进入风险经理决策"
    break
  fi
  sleep 3
done

# 等待风险经理决策完成
for i in {1..20}; do
  STATUS=$(python3 {baseDir}/scripts/intermediate_shared.py --stock-code {股票代码} --status 2>/dev/null)
  if echo "$STATUS" | grep -q "风险经理决策.*done"; then
    echo "风险经理决策完成，进入 PDF 生成"
    break
  fi
  sleep 3
done
```

### Step 6: 生成 PDF

```bash
# 直接从共享文件渲染 PDF，无需在 prompt 里拼接所有数据
python3 {baseDir}/scripts/generate_report.py --from-file $JSON_FILE
```

---

## 各步骤写入规范

| 步骤 | --step 参数 | 写入路径 | 关键约束 |
|------|------------|---------|---------|
| 新闻搜索 | news_data | news_data | summary ≤50字，sentiment ∈{偏多,偏空,中性} |
| 多头分析 | bull_analyst | 结果.多头分析 | confidenceindex 0-1 |
| 空头分析 | bear_analyst | 结果.空头分析 | 同上 |
| 技术分析 | tech_analyst | 结果.技术分析 | 趋势判断键=短期/中期/长期 |
| 基本面分析 | fundamentals_analyst | 结果.基本面分析 | 估值分析键必须用中文 |
| 新闻分析 | news_analyst | 结果.新闻分析 | news_list 每条有 summary |
| 社交媒体分析 | social_analyst | 结果.社交媒体分析 | sentiment_score 0-1 |
| 辩论过程 | debate | 结果.辩论过程 | rounds 是数组 |
| 研究经理决策 | manager | 结果.研究经理决策 | decision ∈{买入,卖出,持有} |
| 交易计划 | trader | 结果.交易计划 | buy/target/stop 必须是数字或 null |
| 风险辩论 | risk_debate | 结果.风险辩论 | 三派结构固定 |
| 风险经理决策 | risk_manager | 结果.风险经理决策 | risk_level ∈{低,中,高} |

---

## 输出文件

PDF 保存到 `{baseDir}/scripts/reports/`，文件名：`{股票代码}_{YYYYMMDD}_{HHMMSS}.pdf`

---

## 调试方法

### 查看当前分析状态
```bash
python3 {baseDir}/scripts/intermediate_shared.py --stock-code PDD --status
```

### 查看共享文件内容
```bash
python3 {baseDir}/scripts/intermediate_shared.py --stock-code PDD --read
```

### 直接生成 PDF（已有共享文件时）
```bash
python3 {baseDir}/scripts/generate_report.py \
  --from-file {baseDir}/scripts/intermediate/PDD_20260520_100000.json
```

### 测试验证工具
```bash
# 测试验证工具（含内容质量检测）
echo '{"bull_detail": {"core_logic": "测试", "bull_case": ["测试"]}}' | \
  python3 {baseDir}/scripts/validate_step.py --step bull_analyst

# 获取默认值
python3 {baseDir}/scripts/validate_step.py --step bull_analyst --default
```

---

## 内容质量要求

validate_step.py 在字段验证通过后，还会检查内容质量（字数下限）：

| 步骤 | 字段 | 最小字数 |
|------|------|---------|
| bull_analyst | core_logic | ≥20字 |
| bull_analyst | bull_case 总计 | ≥50字 |
| bear_analyst | core_logic | ≥20字 |
| bear_analyst | bear_case 总计 | ≥50字 |
| manager | rationale | ≥30字 |

如果内容过短，验证会失败并返回 `content_too_short` 错误，hint 中会说明具体不足原因。Subagent 应根据错误提示补充内容后重试。