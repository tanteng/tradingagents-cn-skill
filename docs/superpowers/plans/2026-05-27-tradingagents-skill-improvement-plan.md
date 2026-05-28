# TradingAgents-CN Skill 改进实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 改进 TradingAgents-CN Skill，解决 subagent 失败率高、文档与脚本不一致、辩论 fallback 逻辑问题

**Architecture:** 分三个 Phase：文档修正 → 脚本改进 → 架构改进。采用渐进式重构，确保每个阶段可独立验证。

**Tech Stack:** Python 3, intermediate_shared.py, pdf_generator.py, SKILL.md

---

## 文件结构

```
scripts/
  intermediate_shared.py    # 修改：添加 --field-map，改进帮助信息
  pdf_generator.py           # 修改：移除 fallback 辩论构造逻辑
SKILL.md                     # 修改：添加字段映射对照表，修正辩论写入规范
references/
  step_schema.json          # 参考：现有字段映射配置
docs/superpowers/plans/
  2026-05-27-tradingagents-skill-improvement-plan.md  # 本计划
```

---

## Task 1: SKILL.md 文档修正

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: 备份并读取当前 SKILL.md**

查看"各步骤写入规范"表（约第 203-219 行）和"调试方法"章节

- [ ] **Step 2: 在"各步骤写入规范"后添加字段映射对照表**

在表格后添加：

```markdown
## 字段映射对照表

`intermediate_shared.py --write --step <step>` 中的 `--step` 参数：
| --step 参数 | 实际写入路径 | 说明 |
|------------|-------------|------|
| stock_data | 结果.股票数据 | 初始化时写入 |
| news_data | news_data | 新闻原始数据 |
| bull_analyst | 结果.多头分析 | 多头分析师结论 |
| bear_analyst | 结果.空头分析 | 空头分析师结论 |
| tech_analyst | 结果.技术分析 | 技术分析师结论 |
| fundamentals_analyst | 结果.基本面分析 | 基本面分析师结论 |
| news_analyst | 结果.新闻分析 | 新闻分析师结论 |
| social_analyst | 结果.社交媒体分析 | 社交媒体分析师结论 |
| debate | 结果.辩论过程 | 必须包含 `rounds` 数组 |
| manager | 结果.研究经理决策 | decision ∈{买入,卖出,持有} |
| trader | 结果.交易计划 | buy/target/stop 必须是数字或 null |
| risk_debate | 结果.风险辩论 | 三派结构：aggressive/neutral/conservative |
| risk_manager | 结果.风险经理决策 | risk_level ∈{低,中,高} |

**注意**：SKILL.md 中旧写法 `--write-stock-data` 不存在，正确写法是 `--write --step stock_data`。
```

- [ ] **Step 3: 修正辩论过程写入说明**

找到辩论过程行：
```markdown
| 辩论过程 | debate | 结果.辩论过程 | rounds 是数组 |
```

替换为：
```markdown
| 辩论过程 | debate | 结果.辩论过程 | 必须包含 `rounds` 数组，每轮含 `bull_detail`/`bear_detail` 结构 |
```

- [ ] **Step 4: 修正技术分析写入说明**

找到技术分析行（约）：
```markdown
| 技术分析 | tech_analyst | 结果.技术分析 | 趋势判断键=短期/中期/长期 |
```

替换为：
```markdown
| 技术分析 | tech_analyst | 结果.技术分析 | 趋势判断键=短期/中期/长期，必须包含 `technical_analysis` 嵌套结构 |
```

- [ ] **Step 5: 验证修改**

确认文档中：
1. 字段映射对照表已添加
2. 所有 `--step` 参数示例为英文字段名
3. 所有结果路径示例为中文路径

- [ ] **Step 6: 提交**

```bash
git add SKILL.md
git commit -m "docs: SKILL.md 添加字段映射对照表，修正辩论写入规范"
```

---

## Task 2: intermediate_shared.py 添加 --field-map

**Files:**
- Modify: `scripts/intermediate_shared.py:144-213`

- [ ] **Step 1: 读取并理解当前 main() 函数结构**

定位 argparse 解析逻辑（约 144-213 行），理解当前参数处理流程

- [ ] **Step 2: 添加 --field-map 参数处理**

在 main() 函数中，在 `--status` 处理前添加：

```python
if args.field_map:
    print("字段映射对照表：")
    print("-" * 60)
    print(f"{'--step 参数':<20} {'写入路径':<30} {'说明'}")
    print("-" * 60)
    for step_en, path in sorted(STEP_RESULT_PATH.items()):
        cn_key = STEP_KEYS.get(step_en, step_en)
        desc = _SCHEMA.get("step_mappings", {}).get(cn_key, {}).get("description", "")
        print(f"{step_en:<20} {path:<30} {desc}")
    print("-" * 60)
    print("提示：--step 参数支持英文（bull_analyst）和中文（多头分析）")
    return
```

在 `parser.add_argument("--status", ...)` 后添加：

```python
parser.add_argument("--field-map", action="store_true", help="显示所有字段映射关系")
```

- [ ] **Step 3: 验证 --field-map 功能**

Run: `python3 scripts/intermediate_shared.py --field-map`
Expected: 输出字段映射对照表

- [ ] **Step 4: 提交**

```bash
git add scripts/intermediate_shared.py
git commit -m "feat(intermediate_shared): 添加 --field-map 显示字段映射对照表"
```

---

## Task 3: pdf_generator.py 移除 fallback 辩论构造逻辑

**Files:**
- Modify: `scripts/pdf_generator.py:190-207`

- [ ] **Step 1: 定位需要删除的代码**

在 `_normalize_shared_schema` 方法中，找到约 190-207 行：

```python
if not result.get("debate", {}).get("rounds"):
    result["debate"] = {
        "rounds": [
            {
                "bull_detail": {
                    "激进派目标收益": risk.get("aggressive", {}).get("target_return", "N/A"),
                    "激进派仓位": risk.get("aggressive", {}).get("position_size", "N/A"),
                    "激进派止损": risk.get("aggressive", {}).get("stop_loss", "N/A"),
                },
                "bear_detail": {
                    "保守派目标收益": risk.get("conservative", {}).get("target_return", "N/A"),
                    "保守派仓位": risk.get("conservative", {}).get("position_size", "N/A"),
                    "保守派止损": risk.get("conservative", {}).get("stop_loss", "N/A"),
                },
            }
        ]
    }
```

- [ ] **Step 2: 删除 fallback 逻辑，保留注释说明**

删除上述代码块，替换为：

```python
# 注意：如果 debate.rounds 不存在，不构造假数据。
# 真实辩论数据应由 subagent 正常写入，若缺失则 PDF 显示"辩论数据未写入"
```

- [ ] **Step 3: 修改辩论数据缺失提示**

在 `_generate_html` 方法中，找到约 525 行：
```html
<p class="no-data">辩论数据待生成</p>
```

替换为：
```html
<p class="no-data">⚠️ 辩论数据未写入或格式不完整，请检查分析流程是否正常完成</p>
```

- [ ] **Step 4: 验证修改**

1. 确认 fallback 代码已删除
2. 确认缺失提示已更新
3. 运行 `python3 scripts/generate_report.py --help` 确保无语法错误

- [ ] **Step 5: 提交**

```bash
git add scripts/pdf_generator.py
git commit -m "fix(pdf_generator): 移除 fallback 辩论构造逻辑，改为明确提示数据缺失"
```

---

## Task 4: SKILL.md 添加预搜索流程说明（Phase 3 准备）

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: 在"Step 2: 并行 spawn 6 个分析师"之前添加预搜索说明**

找到"### Step 2: 并行 spawn 6 个分析师"（约第 82 行），在其前添加：

```markdown
### Step 1.5: 主 agent 预搜索（可选但推荐）

**目的：** 避免 6 个 subagent 同时调用 web_search 导致限流

```bash
# 预搜索新闻和基本信息
echo "开始预搜索股票信息..."
web_search "{股票名称} {股票代码} 最新新闻 2026"
web_search "{股票名称} {股票代码} 最新分析 2026"

# 将搜索结果写入 news_data（subagent 将直接复用，不再调用 web_search）
python3 {baseDir}/scripts/intermediate_shared.py \
  --write --step news_data --data '<预搜索结果JSON>'
```

**注意：** 如果预搜索失败，subagent 将需要自己调用 web_search，建议使用错峰启动（每 3-5 秒启动一个）避免限流。
```

- [ ] **Step 2: 在 subagent 指令模板中说明复用预搜索数据**

找到 subagent 指令模板（约第 120-136 行），将：

```
4. 使用 web_search 搜索近期新闻（{股票代码} {股票名称} 最新新闻）
```

替换为：

```
4. 从共享文件读取 news_data（主 agent 已预搜索）；若数据不足再调用 web_search 补充
```

- [ ] **Step 3: 提交**

```bash
git add SKILL.md
git commit -m "docs: SKILL.md 添加主 agent 预搜索流程说明"
```

---

## Task 5: 验证完整流程

**Files:**
- None (integration test)

- [ ] **Step 1: 测试 intermediate_shared.py --field-map**

Run: `python3 scripts/intermediate_shared.py --field-map`
Expected: 正确显示所有字段映射

- [ ] **Step 2: 测试写入和读取流程**

```bash
# 初始化
JSON_FILE=$(python3 scripts/intermediate_shared.py --init --stock-code TEST --stock-name 测试股票)

# 写入测试
python3 scripts/intermediate_shared.py \
  --write --step bull_analyst \
  --data '{"core_logic": "测试逻辑", "bull_case": ["测试案例1", "测试案例2"], "confidenceindex": 0.75}'

# 读取验证
python3 scripts/intermediate_shared.py --read | grep -A5 "多头分析"
```

Expected: 数据正确写入 `结果.多头分析`

- [ ] **Step 3: 验证 PDF 生成器不构造假辩论数据**

创建一个缺少 debate.rounds 的测试数据，运行 generate_report.py，确认显示"⚠️ 辩论数据未写入"

- [ ] **Step 4: 提交验证结果**

```bash
git add -A
git commit -m "test: 验证完整流程（--field-map、写入、PDF生成）"
```

---

## 验收标准检查清单

- [ ] SKILL.md 添加了字段映射对照表
- [ ] SKILL.md 辩论过程写入说明已修正
- [ ] `intermediate_shared.py --field-map` 正确显示所有映射
- [ ] `intermediate_shared.py --write --step bull_analyst --data '{}'` 能正确写入 `结果.多头分析`
- [ ] pdf_generator.py 移除了 fallback 辩论构造逻辑
- [ ] pdf_generator.py 在辩论数据缺失时显示明确警告而非假数据
- [ ] SKILL.md 添加了主 agent 预搜索流程说明
- [ ] 所有修改已提交到 git