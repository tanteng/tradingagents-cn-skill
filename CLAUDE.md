# TradingAgents-CN Skill 项目规范

## 项目概述

**路径**: `/root/.openclaw/workspace/skills/tradingagents-cn-skill`
**版本**: 2.0.0
**架构**: 17 步多智能体股票分析流程（分析师团队 → 多空辩论 → 风控辩论 → 投资组合经理 → PDF）

---

## 一、数据流核心原则

```
Prompt 定义确切 schema → validate_step.py 验证 → pdf_generator.py 确定读取
```

| 原则 | 说明 |
|------|------|
| **不猜测** | 不用 `.get("毛利率")` 碰运气的写法 |
| **不适配** | 不搞 adapt/兼容层，格式变了就改上下游 |
| **不正则** | 不从自由文本里用正则挖结构化数据 |

---

## 二、17 步工作流

```
Step 1A  → 获取原始文本（截图OCR/文字/代码名称）
Step 1B  → 结构化提取 → stock_data JSON
Step 2   → web_search → news_data JSON
─────────────────────────────────────
Step 3   → tech_analyst JSON → validate
Step 4   → fundamentals_analyst JSON → validate
Step 5   → news_analyst JSON → validate
Step 6   → social_analyst JSON → validate
─────────────────────────────────────
Step 7   → bull_r1 (JSON+debate_text) → validate
Step 8   → bear_r1 (JSON+debate_text) → validate
Step 9   → bull_r2 (JSON+debate_text) → validate
Step 10  → bear_r2 (JSON+debate_text) → validate
─────────────────────────────────────
Step 11  → manager_decision JSON → validate
Step 12  → trading_plan JSON → validate
─────────────────────────────────────
Step 13  → risk_aggressive JSON → validate
Step 14  → risk_conservative JSON → validate
Step 15  → risk_neutral JSON → validate
─────────────────────────────────────
Step 16  → final_decision JSON → validate
Step 17  → 组装 full_report.json → normalize → generate PDF
```

---

## 三、JSON Schema 约定

### 分析师报告（tech/fundamentals/news/social）
```json
{
  "report": "中文长文本分析报告（500字以上）",
  "key_points": ["要点1", "要点2", ...]
}
```

### 辩论步骤（bull_r1/bull_r2/bear_r1/bear_r2）
```json
{
  "debate_text": "中文辩论长文本",
  "core_logic": "核心逻辑1-2句话",
  "bull_case": ["论点1", "论点2", ...],
  "confidence": 0.85
}
```

### 风控辩论（risk_aggressive/risk_conservative/risk_neutral）
```json
{
  "debate_text": "中文辩论长文本",
  "stance": "立场描述",
  "position_size": "30%-40%",
  "key_points": ["要点1", "要点2", ...]
}
```

### trading_plan
```json
{
  "decision": "买入/卖出/观望",
  "buy_price": 1.37,
  "target_price": 1.54,
  "stop_loss": 1.26,
  "reference_price": 1.40,
  "position_size": "15%-20%"
}
```

### final_decision
```json
{
  "rating": "买入/增持/持有/减持/卖出（五级之一）",
  "executive_summary": "执行摘要",
  "investment_thesis": "投资论文",
  "risk_level": "低/中/高"
}
```

---

## 四、validate_step.py 规范

| 组件 | 路径 | 说明 |
|------|------|------|
| `REQUIRED_FIELDS` | `scripts/validate_step.py` | 各步骤必填字段白名单 |
| `FIELD_HINTS` | `scripts/validate_step.py` | 重试时附加到 prompt 的错误提示 |
| `get_default_value()` | `scripts/validate_step.py` | 全部失败时的兜底默认值 |
| 特殊验证 | trader | 买入时 buy_price/target_price/stop_loss 必须是数字 |
| 特殊验证 | portfolio_manager | rating 必须是五级白名单之一 |

### 重试上限
- **关键步骤**（bull_r1/bear_r1/bull_r2/bear_r2/manager/trader/risk_*/portfolio_manager）: 最多 **3 次**
- **次要步骤**（tech/fundamentals/news/social）: 最多 **2 次**

### LLM 调用失败重试（网络/超时）
1. 等 **5 秒**后重新调用同一步骤
2. 最多重试 **2 次**（共 3 次尝试）
3. 3 次都失败 → 获取默认值继续

---

## 五、PDF 生成流程

```
full_report.json → normalize_data.py（规范化） → pdf_generator.py（渲染）
```

### 文件名格式
```
{stock_code}_{stock_name}_{YYYYMMDD}_{HHMMSS}.pdf
例: NET_Cloudflare_20260411.pdf
```

### normalize_data.py 职责
- **不做适配**：只做 schema 映射，不猜测缺失字段
- **不做正则**：从确定的 JSON 结构提取数据
- **透传原则**：已确定结构的字段直接透传

### pdf_generator.py 职责
- 使用 `markdown` 库将 Markdown 转 HTML
- 处理嵌套 JSON 代码块和未闭合标记
- 标题固定为 "TradingAgents-CN Skill"

---

## 六、Prompt 规范

| 规则 | 说明 |
|------|------|
| 全部要求 JSON | 包括辩论步骤，JSON 里放 `debate_text` 长文本字段 |
| 固定 key 名 | financials 用英文 key（pe/pb/roe/gross_margin...），不用中文 |
| 分析师双字段 | `report`（长文本报告）+ `key_points`（要点数组） |
| 辩论双字段 | `debate_text`（自由辩论）+ 结构化字段 |

---

## 七、关键文件索引

| 文件 | 用途 |
|------|------|
| `SKILL.md` | Skill 触发条件和完整工作流定义 |
| `scripts/validate_step.py` | 验证脚本，包含 REQUIRED_FIELDS、FIELD_HINTS、默认值 |
| `scripts/pdf_generator.py` | PDF 生成器（ReportGenerator 类） |
| `scripts/normalize_data.py` | 数据规范化（基于确定 schema 的映射） |
| `scripts/generate_report.py` | CLI 入口，串联 normalize + pdf_generator |
| `references/data_schema.md` | full_report.json 的完整 schema 定义 |
| `references/trader_prompt.md` | 交易员 prompt，价格字段必须是数字 |
| `references/risk_manager_prompt.md` | 投资组合经理 prompt，五级评级 |
| `scripts/results/` | 分析结果 JSON 文件目录 |
| `scripts/reports/` | 生成的 PDF 文件目录 |
| `scripts/logs/` | 日志文件目录 |

---

## 八、调试命令

```bash
# 触发完整分析
openclaw agent --message "分析一下 PDD" --verbose on --json

# 测试验证
echo '<LLM输出>' | python3 scripts/validate_step.py --step tech --stock-code PDD --attempt 1

# 获取默认值
python3 scripts/validate_step.py --step tech --default

# 查看日志
cat scripts/logs/{股票代码}_*.log
```
