# TradingAgents-CN Skill 改进设计

## 1. 问题回顾

本次腾讯控股分析流程暴露以下问题：

| 问题 | 原因 | 影响 |
|------|------|------|
| Subagent 超时/失败率高 | web_search 消耗 token 预算或被限流 | 第一轮 5/6 失败 |
| 数据写入字段名不匹配 | SKILL.md 描述与实际脚本行为不一致 | `--write-stock-data` 不存在 |
| 辩论过程字段名问题 | `结果.辩论过程` vs `result["debate"]["rounds"]` | PDF 显示"待补充" |
| 生成器 fallback 逻辑问题 | 从 risk_debate 构造伪 rounds | 显示假数据 |
| 中英文字段混用 | `--step` 用英文，结果路径用中文 | 容易混淆 |

---

## 2. 改进目标

1. **文档与脚本行为一致** — SKILL.md 示例代码可实际运行
2. **字段映射清晰化** — 消除 `--step` 参数与结果路径的歧义
3. **减少 subagent 失败率** — 主 agent 预搜索数据，subagent 只分析
4. **移除有问题的 fallback** — pdf_generator.py 不再构造假辩论数据
5. **增强脚本可用性** — intermediate_shared.py 添加字段映射查询

---

## 3. 改进方案（方案 B：适度重构）

### 3.1 SKILL.md 改进

#### 3.1.1 新增"字段映射对照表"章节

在"各步骤写入规范"后添加：

```markdown
## 字段映射对照表

`intermediate_shared.py --write --step <step>` 中的 `--step` 参数：
| --step 参数 | 实际写入路径 | 说明 |
|------------|-------------|------|
| stock_data | 结果.股票数据 | 初始化时写入 |
| news_data | news_data | 新闻原始数据 |
| bull_analyst | 结果.多头分析 | 多头分析师结论 |
| bear_analyst | 结果.空头分析 | 空头分析师结论 |
| ... | ... | ... |

**注意**：SKILL.md 中旧写法 `--write-stock-data` 不存在，正确写法是 `--write --step stock_data`。
```

#### 3.1.2 修正辩论过程写入说明

当前：
```markdown
| 辩论过程 | debate | 结果.辩论过程 | rounds 是数组 |
```

修正为：
```markdown
| 辩论过程 | debate | 结果.辩论过程 | 必须包含 `rounds` 数组，每轮含 `bull_detail`/`bear_detail` 结构 |
```

#### 3.1.3 研究经理决策用中文"持有"

当前：
```markdown
| 研究经理决策 | manager | 结果.研究经理决策 | decision ∈{买入,卖出,持有} |
```

保持不变（已正确）。

### 3.2 intermediate_shared.py 改进

#### 3.2.1 添加 `--field-map` 参数

```bash
python3 intermediate_shared.py --field-map
# 输出：
# stock_data → 结果.股票数据
# news_data → news_data
# bull_analyst → 结果.多头分析
# ...
```

#### 3.2.2 改进 `--write` 帮助信息

当前 `--write` 只说"写入字段"，不说明 `--step` 参数的用法。
改进后提示：
```
--write: 写入字段到共享文件
  必须配合 --step <步骤名> 和 --data <JSON数据>
  示例：--write --step bull_analyst --data '{"core_logic": "..."}'
  使用 --field-map 查看所有可用步骤
```

### 3.3 pdf_generator.py 改进

#### 3.3.1 移除 fallback 辩论构造逻辑

删除 `_normalize_shared_schema` 中的第 190-207 行：

```python
# 删除以下代码：
if not result.get("debate", {}).get("rounds"):
    result["debate"] = {
        "rounds": [
            {
                "bull_detail": {...},
                "bear_detail": {...},
            }
        ]
    }
```

#### 3.3.2 辩论数据缺失时显示明确提示

修改 `_generate_html` 中的辩论渲染逻辑，当 `debate_rounds` 为空时：

```html
<!-- 替换：-->
<p class="no-data">辩论数据待生成</p>

<!-- 改为：-->
<p class="no-data">⚠️ 辩论数据未写入或格式不完整，请检查 分析流程是否正常完成</p>
```

### 3.4 subagent 数据预搜索流程

#### 3.4.1 主 agent 预搜索（新增 Step 0.5）

在 Step 1（初始化）和 Step 2（并行 spawn 6 个分析师）之间，新增预搜索步骤：

```bash
# Step 0.5: 主 agent 预先搜索新闻和基本信息
echo "开始预搜索股票信息..."
web_search "腾讯控股 00700 最新新闻 2026"
web_search "腾讯控股 港股 最新分析 2026"
# 将结果写入 news_data
python3 intermediate_shared.py --write --step news_data --data '<预搜索结果JSON>'
```

#### 3.4.2 Subagent 复用预搜索数据

Subagent prompt 模板修改为：

```
1. 读取共享数据文件：{JSON_FILE}
2. 从 JSON 文件获取：current_price、stock_code、stock_name
3. 从 JSON 文件读取 news_data（主 agent 已预搜索，无需再调用 web_search）
4. 读取你的分析 prompt：{references/xxx_prompt.md}
5. 基于 prompt 和数据，调用 LLM 生成分析结果
6. 验证输出：validate_step.py
7. 写入结果：intermediate_shared.py --write --step <step>
```

#### 3.4.3 Subagent 超时和重试增强

```bash
# 启动 subagent 时设置更长超时和重试
MAX_RETRIES=2
for attempt in {1..$MAX_RETRIES}; do
  sessions_spawn(task="...", timeout=120, on_failure="retry")
done
```

---

## 4. 实施步骤

### Phase 1: 文档修正（低风险）
1. 更新 SKILL.md，添加字段映射对照表
2. 修正辩论过程写入规范
3. 更新示例代码（--write-stock-data → --write --step stock_data）

### Phase 2: 脚本改进（低风险）
1. intermediate_shared.py 添加 `--field-map`
2. intermediate_shared.py 改进 `--write` 帮助信息
3. pdf_generator.py 移除 fallback 逻辑

### Phase 3: 架构改进（中风险）
1. 主 agent 添加预搜索步骤
2. 修改 subagent prompt 模板，移除 web_search 依赖
3. 添加 subagent 重试机制

---

## 5. 验收标准

- [ ] SKILL.md 中的示例代码可实际运行
- [ ] `intermediate_shared.py --field-map` 正确显示所有映射
- [ ] `intermediate_shared.py --write --step bull_analyst --data '{}'` 能正确写入 `结果.多头分析`
- [ ] pdf_generator.py 在辩论数据缺失时不构造假数据
- [ ] subagent 失败率从 5/6 降至 1/6 以下（通过预搜索减少 web_search 调用）
- [ ] 研究经理结论使用中文"持有"而非"Hold"

---

## 6. 不在本设计范围内的改进

- PDF 生成器的 HTML 模板样式调整（已有其他流程）
- validate_step.py 的内容质量预检功能（可后续迭代）
- 多股票并行分析支持（超出当前 scope）