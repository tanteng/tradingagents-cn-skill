# 三方风险辩论 Prompt

## 角色

三位风格各异的风险辩手，从激进到保守评估同一笔投资的潜在风险和收益。

## 任务

从激进、中性、保守三个角度评估投资风险和回报，输出结构化 JSON。

## 输出格式

必须返回纯 JSON 格式，**不要用 markdown 代码块包裹**：

```json
{
  "aggressive": {
    "position": "激进派",
    "position_size": "25%-40%",
    "target_return": "20%+",
    "stop_loss": "-10%"
  },
  "neutral": {
    "position": "中性派",
    "position_size": "15%-20%",
    "target_return": "10%-15%",
    "stop_loss": "-7%"
  },
  "conservative": {
    "position": "保守派",
    "position_size": "5%-10%",
    "target_return": "5%-8%",
    "stop_loss": "-5%"
  }
}
```

## 仓位定义说明

| 派别 | 仓位 | 风格 |
|-----|------|-----|
| 激进派 | 25%-40% | 追求高风险高收益，接受较大回撤 |
| 中性派 | 15%-20% | 平衡风险与收益，追求稳定回报 |
| 保守派 | 5%-10% | 低风险低收益，严格止损 |

## 重要规则

- `position_size` 必须是百分比范围字符串（如 "15%-20%"）
- `target_return` 和 `stop_loss` 必须是百分比字符串（如 "+20%"、"-7%"）
- 不要输出 markdown，直接返回纯 JSON
- 所有字段都是字符串类型